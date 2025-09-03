// Implementation of DL6WU's Yagi-Uda algorithm in OpenSCAD
// http://www.ifwtech.co.uk/g3sek/diy-yagi/dl6wu-2006.bas//

C = 299792458; // Speed of light in m/s

// Function to calculate wavelength in meters
function wavelength(frequency) = C / (frequency * 1e6);

// DL6WU spacing table (from BASIC program line 2110-2120)
spacing_table = [
    0.075,  // Director 1 spacing from driven element
    0.180,  // Director 2 spacing from director 1
    0.215,  // Director 3 spacing from director 2
    0.250,  // Director 4 spacing from director 3
    0.280,  // Director 5 spacing from director 4
    0.300,  // Director 6 spacing from director 5
    0.315,  // Director 7 spacing from director 6
    0.330,  // Director 8 spacing from director 7
    0.345,  // Director 9 spacing from director 8
    0.360,  // Director 10 spacing from director 9
    0.375,  // Director 11 spacing from director 10
    0.390,  // Director 12 spacing from director 11
    0.400,  // Director 13 spacing from director 12
    0.400   // Director 14+ spacing (constant)
];

// DL6WU director length calculation coefficients (from BASIC program lines 2160-2220)
// Format: [diameter, K1, K2, K3, K4]
director_coeffs = [
    [0.001, 0.4711, 0.018,   0.08398, 0.965],
    [0.003, 0.462,  0.01941, 0.08543, 0.9697],
    [0.005, 0.4538, 0.02117, 0.0951,  1.007],
    [0.007, 0.4491, 0.02274, 0.08801, 0.9004],
    [0.010, 0.4421, 0.02396, 0.1027,  1.038],
    [0.015, 0.4358, 0.02558, 0.1149,  1.034],
    [0.020, 0.4268, 0.02614, 0.1112,  1.036]
];

// Function to get coefficients for specific diameter using array search
function get_director_coeffs(element_diameter) =
    let(
        // Find the closest diameter entries in the array
        diameters = [for (c = director_coeffs) c[0]],
        // Find index of closest lower bound
        lower_idx = max(0, len([for (d = diameters) if (d <= element_diameter / 1000) d]) - 1),
        // Find index of closest upper bound  
        upper_idx = min(len(diameters) - 1, len([for (d = diameters) if (d < element_diameter / 1000) d]))
    )
    lower_idx == upper_idx ? 
        // Exact match, return those coefficients
        [for (i = [1:4]) director_coeffs[lower_idx][i]] :
    let(
        // Linear interpolation between lower and upper coefficients
        lower = director_coeffs[lower_idx],
        upper = director_coeffs[upper_idx],
        j = (element_diameter - lower[0]) / (upper[0] - lower[0])
    )
    [
        lower[1] + j * (upper[1] - lower[1]),
        lower[2] + j * (upper[2] - lower[2]),
        lower[3] + j * (upper[3] - lower[3]),
        lower[4] + j * (upper[4] - lower[4])
    ];

// Director length calculation (faithful to BASIC line 1490)
function calc_director_length(director_number, element_diameter) =
    let(
        coeffs = get_director_coeffs(element_diameter),
        k1 = coeffs[0],
        k2 = coeffs[1], 
        k3 = coeffs[2],
        k4 = coeffs[3]
    )
    (k1 - k2 * ln(director_number)) * (1 - k3 * exp(-k4 * director_number));

// Reflector length calculation (faithful to BASIC line 1522)
function calc_reflector_length(element_diameter) =
    let(
        xr = 20, // Reflector reactance (DL6WU recommendation)
        denominator = 186.8769 * ln(2 / element_diameter) - 320
    )
    (((xr - 40) / denominator) + 1) / 2;

// Driven element length calculation (faithful to BASIC lines 1530-1540)
function calc_driven_length(element_diameter) =
    let(
        de = (0.4777 - (1.0522 * element_diameter) + (0.43363 * pow(element_diameter, -0.014891))) / 2
    )
    1.02 * de; // 2% longer for better match (DL6WU 1988 modification)

// Calculate cumulative positions along boom (faithful to BASIC lines 1190-1330)
function calc_positions(num_elements) =
    let(
        reflector_pos = 0,
        driven_pos = 0.2, // 0.2λ spacing from reflector (BASIC line 1190)
        
        // Calculate director positions (BASIC lines 1210-1320)
        director_positions = [
            for (i = [0:num_elements-3])
            driven_pos + sum([for (j = [0:i]) 
                (j < len(spacing_table)) ? spacing_table[j] : spacing_table[-1]
            ])
        ]
    )
    concat([reflector_pos, driven_pos], director_positions);

// Helper function to sum array
function sum(arr, i=0, total=0) = 
    i >= len(arr) ? total : sum(arr, i+1, total + arr[i]);

// Main Yagi antenna module
module yagi_antenna(
    frequency = 2400, // MHz
    element_diameter = 1, // mm
    num_elements = 10
) {
    lambda = wavelength(frequency);
    lambda_mm = lambda * 1000;
    element_diameter_lambda = element_diameter / lambda_mm;
    half_wave = lambda_mm / 2;
    
    echo("=== DL6WU YAGI ===");
    echo(str("Frequency: ", frequency, " MHz"));
    echo(str("Wavelength: ", lambda, " m (", lambda_mm, " mm)"));
    echo(str("Element diameter: ", element_diameter, " mm (", element_diameter_lambda, " λ)"));
    echo(str("Number of elements: ", num_elements));
    
    // Test coefficient lookup
    test_coeffs = get_director_coeffs(element_diameter_lambda);
    echo(str("Interpolated coefficients for ", element_diameter_lambda, " λ: K1=", test_coeffs[0], ", K2=", test_coeffs[1], ", K3=", test_coeffs[2], ", K4=", test_coeffs[3]));
    
    // Calculate element lengths using DL6WU algorithms
    reflector_length = calc_reflector_length(element_diameter_lambda) * lambda_mm;
    driven_length = calc_driven_length(element_diameter_lambda) * lambda_mm;
    
    // Calculate director lengths with faithful interpolation
    director_lengths = [for (i = [1:num_elements-2]) 
        calc_director_length(i, element_diameter_lambda) * lambda_mm
    ];
    
    // Calculate positions along boom
    positions_lambda = calc_positions(num_elements);
    positions_mm = [for (p = positions_lambda) p * lambda_mm];
    
    // Combine all element lengths
    element_lengths = concat([reflector_length, driven_length], director_lengths);
    
    // Calculate boom length
    boom_length = positions_mm[num_elements-1];
    
    // Calculate gain using DL6WU formula (BASIC line 610)
    gain_dbd = 9.2 + 3.39 * ln(boom_length / lambda_mm);
    
    echo("\nELEMENT POSITIONS (from reflector):");
    for (i = [0:num_elements-1]) {
        element_type = i == 0 ? "Reflector" : i == 1 ? "Driven" : str("Director ", i-1);
        echo(str(element_type, ": ", positions_mm[i], " mm (", positions_lambda[i], " λ)"));
    }
    
    echo("\nELEMENT LENGTHS:");
    for (i = [0:num_elements-1]) {
        element_type = i == 0 ? "Reflector" : i == 1 ? "Driven" : str("Director ", i-1);
        echo(str(element_type, ": ", element_lengths[i], " mm (", element_lengths[i]/lambda_mm, " λ)"));
    }
    
    echo("\nPERFORMANCE:");
    echo(str("Boom length: ", boom_length, " mm (", boom_length/lambda_mm, " λ)"));
    echo(str("Estimated gain: ", gain_dbd, " dBd"));
    
    // Draw elements
    for (i = [0:num_elements-1]) {
        translate([positions_mm[i], 0, 0]) {
            element_color = 
                i == 0 ? "red" : // Reflector
                i == 1 ? "blue" : // Driven element
                "green"; // Directors
            
            color(element_color) {
                if (i == 1) {
                    // Driven element divided into 2 parts with 1.5*diameter gap
                    gap = 1.5 * element_diameter;
                    half_length = (element_lengths[i] - gap) / 2;
                    
                    // Left half (negative Y direction)
                    translate([0, -half_length/2 - gap/2, 0])
                    rotate([90, 0, 0])
                    cylinder(h = half_length, d = element_diameter, center = true);
                    
                    // Right half (positive Y direction)  
                    translate([0, half_length/2 + gap/2, 0])
                    rotate([90, 0, 0])
                    cylinder(h = half_length, d = element_diameter, center = true);
                } else {
                    // Reflector and directors (full elements along Y axis)
                    rotate([90, 0, 0])
                    cylinder(h = element_lengths[i], d = element_diameter, center = true);
                }
            }
        }
    }
}

yagi_antenna(2400, 1, 10);
