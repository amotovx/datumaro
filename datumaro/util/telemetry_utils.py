# Copyright (C) 2021 Intel Corporation
#
# SPDX-License-Identifier: MIT

import json
import os
import re
import sys
import traceback

from datumaro.cli import commands, contexts

try:
    import openvino_telemetry as tm
except ImportError:
    from datumaro.util import telemetry_stub as tm

def _get_action_name(command):
    if command is contexts.project.export_command:
        return 'project_export_result'
    elif command is contexts.project.filter_command:
        return 'project_filter_result'
    elif command is contexts.project.transform_command:
        return 'project_transform_result'
    elif command is contexts.project.info_command:
        return 'project_info_result'
    elif command is contexts.project.stats_command:
        return 'project_stats_result'
    elif command is contexts.project.validate_command:
        return 'project_validate_result'
    elif command is contexts.project.migrate_command:
        return 'project_migrate_result'
    elif command is contexts.source.add_command:
        return 'source_add_result'
    elif command is contexts.source.remove_command:
        return 'source_remove_result'
    elif command is contexts.source.info_command:
        return 'source_info_result'
    elif command is contexts.model.add_command:
        return 'model_add_result'
    elif command is contexts.model.remove_command:
        return 'model_remove_result'
    elif command is contexts.model.run_command:
        return 'model_run_result'
    elif command is contexts.model.info_command:
        return 'model_info_result'
    elif command is commands.checkout:
        return 'checkout_result'
    elif command is commands.commit:
        return 'commit_result'
    elif command is commands.convert:
        return 'convert_result'
    elif command is commands.create:
        return 'create_result'
    elif command is commands.diff:
        return 'diff_result'
    elif command is commands.explain:
        return 'explain_result'
    elif command is commands.explain:
        return 'explain_result'
    elif command is commands.info:
        return 'info_result'
    elif command is commands.log:
        return 'log_result'
    elif command is commands.merge:
        return 'merge_result'
    elif command is commands.status:
        return 'status_result'

    return 'unknown_command_result'

def _cleanup_params_info(args, params_with_paths):
    fields_to_exclude = ('command', '_positionals',)
    cli_params = {}
    for arg in vars(args):
        if arg in fields_to_exclude:
            continue
        arg_value = getattr(args, arg)
        if arg in params_with_paths:
            # If command line argument value is a directory or a path to file it is not sent
            # as it may contain confidential information. "1" value is used instead.
            cli_params[arg] = str(1)
        else:
            cli_params[arg] = str(arg_value)
    return cli_params

def _cleanup_stacktrace():
    installation_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def clean_path(match):
        file_path = match.group(1)
        if file_path.startswith(installation_dir):
            file_path = os.path.relpath(file_path, installation_dir)
        else:
            file_path = os.path.basename(file_path)

        return 'File "{}"'.format(file_path)

    exc_type, _, exc_traceback = sys.exc_info()
    tb_lines = traceback.format_list(traceback.extract_tb(exc_traceback))
    tb_lines = [re.sub(r'File "([^"]+)"', clean_path, line, 1) for line in tb_lines]

    return exc_type.__name__, ''.join(tb_lines)

def init_telemetry_session(app_name, app_version):
    telemetry = tm.Telemetry(app_name=app_name, app_version=app_version, tid='UA-114865019-4')
    telemetry.start_session('dm')
    telemetry.send_event('dm', 'version', app_version)

    return telemetry

def close_telemetry_session(telemetry):
    telemetry.end_session('dm')
    telemetry.force_shutdown(1.0)

def _send_result_info(result, telemetry, args, sensetive_params):
    payload = {
        'status': result,
        **_cleanup_params_info(args, sensetive_params),
    }
    action = _get_action_name(args.command)
    telemetry.send_event('dm', action, json.dumps(payload))

def send_version_info(telemetry, version):
    telemetry.send_event('dm', version, str(version))

def send_command_success_info(telemetry, args, sensetive_params):
    _send_result_info('success', telemetry, args, sensetive_params)

def send_command_failure_info(telemetry, args, sensetive_params):
    _send_result_info('failure', telemetry, args, sensetive_params)

def send_command_exception_info(telemetry, args, sensetive_params):
    _send_result_info('exception', telemetry, args, sensetive_params)
    send_error_info(telemetry, args, sensetive_params)

def send_error_info(telemetry, args, sensetive_params):
    exc_type, stack_trace = _cleanup_stacktrace()
    payload = {
        'exception_type': exc_type,
        'stack_trace': stack_trace,
        **_cleanup_params_info(args, sensetive_params),
    }

    telemetry.send_event('dm', 'error', json.dumps(payload))
