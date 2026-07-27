# Read the file
python -m agent.cli run --task "Read dummy.txt" --run-id run_read_01
# Replay task trace
python -m agent.cli replay run_read_01

# Write file
python -m agent.cli run --task "Write notes.txt with content 'Hello from CLI'" --run-id run_write_01
# Replay task trace
python -m agent.cli replay run_write_01

# Code execution
python -m agent.cli run --task "Run python math calculation" --run-id run_py_01
# Replay task trace
python -m agent.cli replay run_py_01


eg : 2
python -m agent.cli run --task "Run python code 'for i in range(1, 4): print(i)'" --run-id run_py_07

python -m agent.cli replay run_py_07