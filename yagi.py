import cadquery as cq
import math
from ocp_vscode import show

# Implementation of DL6WU's Yagi-Uda algorithm in CadQuery
# http://www.ifwtech.co.uk/g3sek/diy-yagi/dl6wu-2006.bas

C = 299792458  # Speed of light in m/s

# Function to calculate wavelength in meters
def wavelength(frequency):
    return C / (frequency * 1e6)

# DL6WU spacing table (from BASIC program line 2110-2120)
spacing_table = [
    0.075,  # Director 1 spacing from driven element
    0.180,  # Director 2 spacing from director 1
    0.215,  # Director 3 spacing from director 2
    0.250,  # Director 4 spacing from director 3
    0.280,  # Director 5 spacing from director 4
    0.300,  # Director 6 spacing from director 5
    0.315,  # Director 7 spacing from director 6
    0.330,  # Director 8 spacing from director 7
    0.345,  # Director 9 spacing from director 8
    0.360,  # Director 10 spacing from director 9
    0.375,  # Director 11 spacing from director 10
    0.390,  # Director 12 spacing from director 11
    0.400,  # Director 13 spacing from director 12
    0.400,  # Director 14+ spacing (constant)
]

# DL6WU director length calculation coefficients (from BASIC program lines 2160-2220)
# Format: [diameter, K1, K2, K3, K4]
director_coeffs = [
    [0.001, 0.4711, 0.018, 0.08398, 0.965],
    [0.003, 0.462, 0.01941, 0.08543, 0.9697],
    [0.005, 0.4538, 0.02117, 0.0951, 1.007],
    [0.007, 0.4491, 0.02274, 0.08801, 0.9004],
    [0.010, 0.4421, 0.02396, 0.1027, 1.038],
    [0.015, 0.4358, 0.02558, 0.1149, 1.034],
    [0.020, 0.4268, 0.02614, 0.1112, 1.036],
]

# Function to get coefficients for specific diameter using array search
def get_director_coeffs(element_diameter):
    # Find the closest diameter entries in the array
    diameters = [c[0] for c in director_coeffs]

    # Find index of closest lower bound
    lower_idx = max(0, len([d for d in diameters if d <= element_diameter / 1000]) - 1)

    # Find index of closest upper bound
    upper_idx = min(len(diameters) - 1, len([d for d in diameters if d < element_diameter / 1000]))

    if lower_idx == upper_idx:
        # Exact match, return those coefficients
        return [director_coeffs[lower_idx][i] for i in range(1, 5)]
    else:
        # Linear interpolation between lower and upper coefficients
        lower = director_coeffs[lower_idx]
        upper = director_coeffs[upper_idx]
        j = (element_diameter - lower[0]) / (upper[0] - lower[0])
        return [
            lower[1] + j * (upper[1] - lower[1]),
            lower[2] + j * (upper[2] - lower[2]),
            lower[3] + j * (upper[3] - lower[3]),
            lower[4] + j * (upper[4] - lower[4]),
        ]

# Director length calculation (faithful to BASIC line 1490)
def calc_director_length(director_number, element_diameter):
    coeffs = get_director_coeffs(element_diameter)
    k1, k2, k3, k4 = coeffs
    return (k1 - k2 * math.log(director_number)) * (1 - k3 * math.exp(-k4 * director_number))

# Reflector length calculation (faithful to BASIC line 1522)
def calc_reflector_length(element_diameter):
    xr = 20  # Reflector reactance (DL6WU recommendation)
    denominator = 186.8769 * math.log(2 / element_diameter) - 320
    return ((xr - 40) / denominator + 1) / 2

# Driven element length calculation (faithful to BASIC lines 1530-1540)
def calc_driven_length(element_diameter):
    de = (0.4777 - (1.0522 * element_diameter) + (0.43363 * element_diameter ** (-0.014891))) / 2
    return 1.02 * de  # 2% longer for better match (DL6WU 1988 modification)

# Calculate cumulative positions along boom
def calc_positions(num_elements):
    reflector_pos = 0
    driven_pos = 0.2  # 0.2λ spacing from reflector (BASIC line 1190)

    # Calculate director positions
    director_positions = []
    for i in range(num_elements - 2):
        position = driven_pos
        for j in range(i + 1):
            if j < len(spacing_table):
                position += spacing_table[j]
            else:
                position += spacing_table[-1]
        director_positions.append(position)

    return [reflector_pos, driven_pos] + director_positions

# Main Yagi antenna function
def yagi_antenna(frequency=2400, element_diameter=1, num_elements=10, gap=1.5):
    lambda_val = wavelength(frequency)
    lambda_mm = lambda_val * 1000
    element_diameter_lambda = element_diameter / lambda_mm

    print("=== DL6WU YAGI ===")
    print(f"Frequency: {frequency} MHz")
    print(f"Wavelength: {lambda_val} m ({lambda_mm} mm)")
    print(f"Element diameter: {element_diameter} mm ({element_diameter_lambda} λ)")
    print(f"Number of elements: {num_elements}")

    # Calculate element lengths using DL6WU algorithms
    reflector_length = calc_reflector_length(element_diameter_lambda) * lambda_mm
    driven_length = calc_driven_length(element_diameter_lambda) * lambda_mm

    # Calculate director lengths
    director_lengths = [
        calc_director_length(i + 1, element_diameter_lambda) * lambda_mm
        for i in range(num_elements - 2)
    ]

    # Calculate positions along boom
    positions_lambda = calc_positions(num_elements)
    positions_mm = [p * lambda_mm for p in positions_lambda]

    # Combine all element lengths
    element_lengths = [reflector_length, driven_length] + director_lengths

    # Calculate boom length
    boom_length = positions_mm[-1]

    # Calculate gain using DL6WU formula (BASIC line 610)
    gain_dbd = 9.2 + 3.39 * math.log(boom_length / lambda_mm)

    print("\nELEMENT POSITIONS (from reflector):")
    for i in range(num_elements):
        element_type = "Reflector" if i == 0 else "Driven" if i == 1 else f"Director {i-1}"
        print(f"{element_type}: {positions_mm[i]} mm ({positions_lambda[i]} λ)")

    print("\nELEMENT LENGTHS:")
    for i in range(num_elements):
        element_type = "Reflector" if i == 0 else "Driven" if i == 1 else f"Director {i-1}"
        print(f"{element_type}: {element_lengths[i]} mm ({element_lengths[i] / lambda_mm} λ)")

    print("\nPERFORMANCE:")
    print(f"Boom length: {boom_length} mm ({boom_length / lambda_mm} λ)")
    print(f"Estimated gain: {gain_dbd} dB")

    # Create the Yagi antenna assembly
    assembly = cq.Assembly(name="antenna")

    # Draw elements
    for i in range(num_elements):
        position = positions_mm[i]
        length = element_lengths[i]

        if i == 1:  # Driven element
            # Driven element divided into 2 parts with gap
            gap_total = gap * element_diameter
            half_length = (length - gap_total) / 2

            # Left half
            left_half = (
                cq.Workplane("XZ")
                .workplane(offset=position)
                .transformed(offset=cq.Vector(-half_length/2 - gap_total/2, 0, 0))
                .cylinder(half_length, element_diameter/2, centered=(True, True, True))
                .rotateAboutCenter(cq.Vector(0,0,1), 90)
            )

            # Right half
            right_half = (
                cq.Workplane("XZ")
                .workplane(offset=position)
                .transformed(offset=cq.Vector(half_length/2 + gap_total/2, 0, 0))
                .cylinder(half_length, element_diameter/2, centered=(True, True, True))
                .rotateAboutCenter(cq.Vector(0,0,1), 90)
            )

            assembly.add(left_half, name=f"driven_left", color=cq.Color(0, 0, 1))  # blue
            assembly.add(right_half, name=f"driven_right", color=cq.Color(0, 0, 1))  # blue

        else:  # Reflector and directors
            element = (
                cq.Workplane("XZ")
                .workplane(offset=position)
                .cylinder(length, element_diameter/2, centered=(True, True, True))
                .rotateAboutCenter(cq.Vector(0,0,1), 90)
            )

            color = cq.Color(1, 0, 0) if i == 0 else cq.Color(0, 1, 0)  # red for reflector, green for directors
            element_name = "reflector" if i == 0 else f"director_{i-1}"
            assembly.add(element, name=element_name, color=color)

    return assembly

# Antenna holder function
def antenna_holder(frequency=2400, element_diameter=1, num_elements=10, gap=1.5, wire_outer_diameter=3):
    lambda_val = wavelength(frequency)
    lambda_mm = lambda_val * 1000
    element_diameter_lambda = element_diameter / lambda_mm

    # TOLERANCES for 3D printing antenna holder
    extra_width = 0.2 * element_diameter
    extra_length = 0.2 * element_diameter
    extra_side = 10 #mm. amount of material for holders, added to the sides along elements
    boom_size = 10 #mm. both boom width/2 and height
    ##########################################

    # Calculate element lengths using DL6WU algorithms
    reflector_length = calc_reflector_length(element_diameter_lambda) * lambda_mm
    driven_length = calc_driven_length(element_diameter_lambda) * lambda_mm + gap

    # Calculate director lengths
    director_lengths = [
        calc_director_length(i + 1, element_diameter_lambda) * lambda_mm
        for i in range(num_elements - 2)
    ]

    # Calculate positions along boom
    positions_lambda = calc_positions(num_elements)
    positions_mm = [p * lambda_mm for p in positions_lambda]

    # Combine all element lengths
    element_lengths = [reflector_length, driven_length] + director_lengths

    # Create holder assembly
    holder_assembly = cq.Assembly(name="holder")

    boom = (
        cq.Workplane("XY")
        .box(boom_size * 2, positions_mm[num_elements-1], boom_size)
        .translate(cq.Vector(0, -positions_mm[num_elements-1]/2, 0))
    )

    holder_assembly.add(boom, name=f"boom", color=cq.Color(0.5, 0.5, 0.5))  # grey
    
    # Draw holder elements
    for i in range(num_elements):
        if i == num_elements - 1:
            distance_to_next = positions_mm[-1] - positions_mm[-2]
        else:
            distance_to_next = positions_mm[i + 1] - positions_mm[i]

        holder = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -positions_mm[i], 0))
            .box(element_lengths[i] + extra_side, distance_to_next / 2, boom_size)
            .edges("|Z").fillet(element_diameter*2)
        )

        holder_assembly.add(holder, name=f"holder_{i}", color=cq.Color(0.5, 0, 0.5))  # purple


    compound = holder_assembly.toCompound()

    for i in range(num_elements):
        # Cut slot for element
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -positions_mm[i], 0))
            .box(element_lengths[i] + extra_length, element_diameter + extra_width, 100)
            .translate((0, 0, -50))
        )

        compound = compound.cut(slot.val()) # pyright: ignore[]
        
    wire_slot = (
            cq.Workplane("XY")
            .cylinder(100, wire_outer_diameter/2)
            .translate(cq.Vector(0, -positions_mm[1], 0))
    ) 
    compound = compound.cut(wire_slot.val())

    return compound

# Create the Yagi antenna and holder
if __name__ == "__main__":
    yagi = yagi_antenna(frequency=2400, element_diameter=1, num_elements=10, gap=1.5)
    holder = antenna_holder(frequency=2400, element_diameter=1, num_elements=10, gap=1.5, wire_outer_diameter=3)

    # Show the results
    show(yagi, holder)
    holder.export("./yagi.stl")
