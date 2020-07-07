# This file is part of arduino-cli.
#
# Copyright 2020 ARDUINO SA (http://www.arduino.cc/)
#
# This software is released under the GNU General Public License version 3,
# which covers the main part of arduino-cli.
# The terms of this license can be found at:
# https://www.gnu.org/licenses/gpl-3.0.en.html
#
# You can be released from the requirements of the above licenses by purchasing
# a commercial license. Buying such a license is mandatory if you want to modify or
# otherwise use the software for commercial activities involving the Arduino
# software without disclosing the source code of your own applications. To purchase
# a commercial license, send an email to license@arduino.cc.
import json
import os
import platform

import pytest

from .common import running_on_ci


def test_compile_without_fqbn(run_command):
    # Init the environment explicitly
    result = run_command("core update-index")
    assert result.ok

    # Download latest AVR
    result = run_command("core install arduino:avr")
    assert result.ok

    # Build sketch without FQBN
    result = run_command("compile")
    assert result.failed


def test_compile_with_simple_sketch(run_command, data_dir, working_dir):
    # Init the environment explicitly
    result = run_command("core update-index")
    assert result.ok

    # Download latest AVR
    result = run_command("core install arduino:avr")
    assert result.ok

    sketch_name = "CompileIntegrationTest"
    sketch_path = os.path.join(data_dir, sketch_name)
    fqbn = "arduino:avr:uno"

    # Create a test sketch
    result = run_command("sketch new {}".format(sketch_path))
    assert result.ok
    assert "Sketch created in: {}".format(sketch_path) in result.stdout

    # Build sketch for arduino:avr:uno
    log_file_name = "compile.log"
    log_file_path = os.path.join(data_dir, log_file_name)
    result = run_command(
        "compile -b {fqbn} {sketch_path} --log-format json --log-file {log_file} --log-level trace".format(
            fqbn=fqbn, sketch_path=sketch_path, log_file=log_file_path
        )
    )
    assert result.ok

    # let's test from the logs if the hex file produced by successful compile is moved to our sketch folder
    log_json = open(log_file_path, "r")
    json_log_lines = log_json.readlines()
    expected_trace_sequence = [
        "Compile {sketch} for {fqbn} started".format(sketch=sketch_path, fqbn=fqbn),
        "Compile {sketch} for {fqbn} successful".format(sketch=sketch_name, fqbn=fqbn),
    ]
    assert is_message_sequence_in_json_log_traces(
        expected_trace_sequence, json_log_lines
    )

    # Test the --output-dir flag with absolute path
    target = os.path.join(data_dir, "test_dir")
    result = run_command(
        "compile -b {fqbn} {sketch_path} --output-dir {target}".format(
            fqbn=fqbn, sketch_path=sketch_path, target=target
        )
    )
    assert result.ok
    assert os.path.exists(target) and os.path.isdir(target)


@pytest.mark.skipif(
    running_on_ci() and platform.system() == "Windows",
    reason="Test disabled on Github Actions Win VM until tmpdir inconsistent behavior bug is fixed",
)
def test_output_flag_default_path(run_command, data_dir, working_dir):
    # Init the environment explicitly
    result = run_command("core update-index")
    assert result.ok

    # Download latest AVR
    result = run_command("core install arduino:avr")
    assert result.ok

    # Create a test sketch
    sketch_path = os.path.join(data_dir, "test_output_flag_default_path")
    fqbn = "arduino:avr:uno"
    result = run_command("sketch new {}".format(sketch_path))
    assert result.ok

    # Test the --output-dir flag defaulting to current working dir
    result = run_command(
        "compile -b {fqbn} {sketch_path} --output-dir test".format(
            fqbn=fqbn, sketch_path=sketch_path
        )
    )
    assert result.ok
    target = os.path.join(working_dir, "test")
    assert os.path.exists(target) and os.path.isdir(target)


def test_compile_with_sketch_with_symlink_selfloop(run_command, data_dir):
    # Init the environment explicitly
    result = run_command("core update-index")
    assert result.ok

    # Download latest AVR
    result = run_command("core install arduino:avr")
    assert result.ok

    sketch_name = "CompileIntegrationTestSymlinkSelfLoop"
    sketch_path = os.path.join(data_dir, sketch_name)
    fqbn = "arduino:avr:uno"

    # Create a test sketch
    result = run_command("sketch new {}".format(sketch_path))
    assert result.ok
    assert "Sketch created in: {}".format(sketch_path) in result.stdout

    # create a symlink that loops on himself
    loop_file_path = os.path.join(sketch_path, "loop")
    os.symlink(loop_file_path, loop_file_path)

    # Build sketch for arduino:avr:uno
    result = run_command(
        "compile -b {fqbn} {sketch_path}".format(fqbn=fqbn, sketch_path=sketch_path)
    )
    # The assertion is a bit relaxed in this case because win behaves differently from macOs and linux
    # returning a different error detailed message
    assert "Error during sketch processing" in result.stderr
    assert not result.ok

    sketch_name = "CompileIntegrationTestSymlinkDirLoop"
    sketch_path = os.path.join(data_dir, sketch_name)
    fqbn = "arduino:avr:uno"

    # Create a test sketch
    result = run_command("sketch new {}".format(sketch_path))
    assert result.ok
    assert "Sketch created in: {}".format(sketch_path) in result.stdout

    # create a symlink that loops on the upper level
    loop_dir_path = os.path.join(sketch_path, "loop_dir")
    os.mkdir(loop_dir_path)
    loop_dir_symlink_path = os.path.join(loop_dir_path, "loop_dir_symlink")
    os.symlink(loop_dir_path, loop_dir_symlink_path)

    # Build sketch for arduino:avr:uno
    result = run_command(
        "compile -b {fqbn} {sketch_path}".format(fqbn=fqbn, sketch_path=sketch_path)
    )
    # The assertion is a bit relaxed also in this case because macOS behaves differently from win and linux:
    # the cli does not follow recursively the symlink til breaking
    assert "Error during sketch processing" in result.stderr
    assert not result.ok


@pytest.mark.skipif(running_on_ci(), reason="VMs have no serial ports")
def test_compile_and_upload_combo(run_command, data_dir, detected_boards):
    # Init the environment explicitly
    result = run_command("core update-index")
    assert result.ok

    # Install required core(s)
    result = run_command("core install arduino:avr")
    result = run_command("core install arduino:samd")
    assert result.ok

    # Create a test sketch
    sketch_name = "CompileAndUploadIntegrationTest"
    sketch_path = os.path.join(data_dir, sketch_name)
    result = run_command("sketch new {}".format(sketch_path))
    assert result.ok
    assert "Sketch created in: {}".format(sketch_path) in result.stdout

    # Build sketch for each detected board
    for board in detected_boards:
        log_file_name = "{fqbn}-compile.log".format(fqbn=board.fqbn.replace(":", "-"))
        log_file_path = os.path.join(data_dir, log_file_name)
        command_log_flags = "--log-format json --log-file {} --log-level trace".format(
            log_file_path
        )

        def run_test(s):
            result = run_command(
                "compile -b {fqbn} --upload -p {address} {sketch_path} {log_flags}".format(
                    fqbn=board.fqbn,
                    address=board.address,
                    sketch_path=s,
                    log_flags=command_log_flags,
                )
            )
            assert result.ok

            # check from the logs if the bin file were uploaded on the current board
            log_json = open(log_file_path, "r")
            json_log_lines = log_json.readlines()
            expected_trace_sequence = [
                "Compile {sketch} for {fqbn} started".format(
                    sketch=sketch_path, fqbn=board.fqbn
                ),
                "Compile {sketch} for {fqbn} successful".format(
                    sketch=sketch_name, fqbn=board.fqbn
                ),
                "Upload {sketch} on {fqbn} started".format(
                    sketch=sketch_path, fqbn=board.fqbn
                ),
                "Upload successful",
            ]
            assert is_message_sequence_in_json_log_traces(
                expected_trace_sequence, json_log_lines
            )

        run_test(sketch_path)


def is_message_sequence_in_json_log_traces(message_sequence, log_json_lines):
    trace_entries = []
    for entry in log_json_lines:
        entry = json.loads(entry)
        if entry.get("level") == "trace":
            if entry.get("msg") in message_sequence:
                trace_entries.append(entry.get("msg"))
    return message_sequence == trace_entries


def test_compile_blacklisted_sketchname(run_command, data_dir):
    """
    Compile should ignore folders named `RCS`, `.git` and the likes, but
    it should be ok for a sketch to be named like RCS.ino
    """
    # Init the environment explicitly
    result = run_command("core update-index")
    assert result.ok

    # Download latest AVR
    result = run_command("core install arduino:avr")
    assert result.ok

    sketch_name = "RCS"
    sketch_path = os.path.join(data_dir, sketch_name)
    fqbn = "arduino:avr:uno"

    # Create a test sketch
    result = run_command("sketch new {}".format(sketch_path))
    assert result.ok
    assert "Sketch created in: {}".format(sketch_path) in result.stdout

    # Build sketch for arduino:avr:uno
    log_file_name = "compile.log"
    log_file_path = os.path.join(data_dir, log_file_name)
    result = run_command(
        "compile -b {fqbn} {sketch_path}".format(fqbn=fqbn, sketch_path=sketch_path)
    )
    assert result.ok


def test_compile_without_precompiled_libraries(run_command, data_dir):
    # Init the environment explicitly
    url = "https://adafruit.github.io/arduino-board-index/package_adafruit_index.json"
    result = run_command("core update-index --additional-urls={}".format(url))
    assert result.ok
    result = run_command("core install arduino:mbed --additional-urls={}".format(url))
    assert result.ok
    result = run_command("core install arduino:samd --additional-urls={}".format(url))
    assert result.ok
    result = run_command("core install adafruit:samd --additional-urls={}".format(url))
    assert result.ok

    # Install pre-release version of Arduino_TensorFlowLite (will be officially released
    # via lib manager after https://github.com/arduino/arduino-builder/issues/353 is in)
    import zipfile
    with zipfile.ZipFile("test/testdata/Arduino_TensorFlowLite.zip", 'r') as zip_ref:
        zip_ref.extractall("{}/libraries/".format(data_dir))
    result = run_command("lib install Arduino_LSM9DS1@1.1.0")
    assert result.ok
    result = run_command(
        "compile -b arduino:mbed:nano33ble {}/libraries/Arduino_TensorFlowLite/examples/magic_wand/".format(data_dir))
    assert result.ok
    result = run_command(
        "compile -b adafruit:samd:adafruit_feather_m4 {}/libraries/Arduino_TensorFlowLite/examples/magic_wand/".format(
            data_dir))
    assert result.ok

    # Non-precompiled version of Arduino_TensorflowLite
    result = run_command("lib install Arduino_TensorflowLite@1.15.0-ALPHA")
    assert result.ok
    result = run_command(
        "compile -b arduino:mbed:nano33ble {}/libraries/Arduino_TensorFlowLite/examples/magic_wand/".format(data_dir))
    assert result.ok
    result = run_command(
        "compile -b adafruit:samd:adafruit_feather_m4 {}/libraries/Arduino_TensorFlowLite/examples/magic_wand/".format(
            data_dir))
    assert result.ok

    # Bosch sensor library
    result = run_command("lib install \"BSEC Software Library@1.5.1474\"")
    assert result.ok
    result = run_command(
        "compile -b arduino:samd:mkr1000 {}/libraries/BSEC_Software_Library/examples/basic/".format(data_dir))
    assert result.ok
    result = run_command(
        "compile -b arduino:mbed:nano33ble {}/libraries/BSEC_Software_Library/examples/basic/".format(data_dir))
    assert result.ok
