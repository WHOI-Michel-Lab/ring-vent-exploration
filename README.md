# ring-vent-exploration


# File Organization
|ring-vent-exploration/
    | data/
        | J21393/
            | csv/
            | obs/
            | ct2/
            | ...
        | ring_depths.csv
    | data_processing/
    


# Tools: 
data_processing/combine_data.py
- Use to turn a directory of sensor readouts into a more structured csv file.
- (Works in a prestructured way, would have to be updated to suit different data specs)

data_processing/rov_sim.py
- Use to visualize the sensor readouts in space with video (when captured)

data_processing/visualize_mass_spec.py
- Use to look at the mass spectrometry density at a given time. 
- Also contains tools for extracting the cleaned up wide and long transformations
- The script itself will output a matplotlib plot of the readout closest to the given time.