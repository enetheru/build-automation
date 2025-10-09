#!/usr/bin/env python3
import argparse
import json
import os
import re
from argparse import RawTextHelpFormatter
from types import SimpleNamespace
from typing import List, Dict, Optional, Tuple, Set

from rich.console import Console
from rich.table import Table

import format as fmt  # Assuming this is a custom module; no changes needed.

script_path = os.path.abspath(__file__)

def load_json(json_file: str) -> List[Dict]:
    """Load and validate the compile_commands.json file."""
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"Error: {json_file} does not exist.")
    with open(json_file, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Error: Invalid JSON in {json_file}: {e}")

def split_command(command: str) -> List[str]:
    """Split a command into tokens, handling MSVC and GCC-style arguments."""
    if command.startswith(('clang-cl', 'cl ', 'link ', 'lib ')):
        return re.findall(r'"[^"]*"|[^\s"]+', command)
    return command.split()

def load_glossary_config() -> Dict[str, Dict[str, str]]:
    """Load flag descriptions and links from a glossary config file."""
    directory = os.path.dirname(script_path)
    glossary_file = os.path.join(directory, 'flag_glossary.json')
    if not os.path.exists(glossary_file):
        raise FileNotFoundError(f"Error: {glossary_file} does not exist. Please provide a valid glossary JSON file.")
    with open(glossary_file, 'r') as f:
        # Assume JSON as {flag: {"description": "...", "link": "..."}}}
        return json.load(f)

def parse_build_log(log_file: str) -> List[Dict]:
    """Parse a build log to extract commands."""
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Error: {log_file} does not exist.")
    with open(log_file, 'r') as f:
        lines = f.readlines()

    commands = []
    current_command = ""
    for line in lines:
        line = line.strip()
        if line.endswith(".exe") or line.startswith(("cl ", "link ", "lib ", "clang-cl ")):
            if current_command:
                commands.append({"command": current_command, "file": ""})  # File not available in log
            current_command = line
        elif current_command:
            current_command += " " + line
    if current_command:
        commands.append({"command": current_command, "file": ""})

    return commands


def extract_config(sourcedir: str, builddir: str, raw_command: str) -> SimpleNamespace:
    """Extract configuration from directories and command."""
    sourcedir_values = os.path.basename(sourcedir).split('.')
    sourcedir_keys = ['host', 'buildtool', 'toolchain', 'godotcpp_target', 'variant']
    config_dict = {k: v for k, v in zip(sourcedir_keys, sourcedir_values)}

    if config_dict.get('buildtool') == 'cmake':
        builddir_values = os.path.basename(builddir).split('-')
        builddir_keys = ['stub', 'toolchain', 'godotcpp_target', 'variant', 'type']
        config_dict.update({k: v for k, v in zip(builddir_keys, builddir_values)})

    name_parts = [
        config_dict.get('host'),
        config_dict.get('buildtool'),
        config_dict.get('toolchain'),
        config_dict.get('godotcpp_target'),
        config_dict.get('variant'),
        config_dict.get('type'),
    ]
    config_dict['name'] = ' '.join([part for part in name_parts if part is not None])
    config_dict['raw_command'] = raw_command
    config_dict['sourcedir'] = sourcedir
    config_dict['builddir'] = builddir
    return SimpleNamespace(**config_dict)


def display_glossary(glossary, all_flags: Dict[str, Dict[str, List[str]]]):
    """Display a glossary of all flags with their descriptions and links."""
    console = Console()
    table = Table(title="Build Flags Glossary", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Flag", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Link", style="blue", overflow='fold')

    # Collect all flags by category
    collected_flags = {}
    for cmd_type, categories in all_flags.items():
        for category, tokens in categories.items():
            if category not in collected_flags:
                collected_flags[category] = set()
            collected_flags[category].update(tokens)

    # Display sorted by category, then flag
    row_index = 0
    for category in sorted(collected_flags.keys()):
        for flag in sorted(collected_flags[category]):
            entry = glossary.get(flag, {'description': "No description available.", 'link': ""})
            description = entry['description']
            link = entry['link']
            row_style = "on #333333" if row_index % 2 == 0 else None
            table.add_row(category.capitalize(), flag, description, link, style=row_style)
            row_index += 1

    console.print(table)


class CompileCommandsCleaner:
    def __init__(self):
        self.config = {
            'line_match': re.compile(
                r'cmake|scons|ninja|'
                r'editor_plugin_registration\.cpp|'
                r'libgdexample.*\.dll|'
                r'libgodot-cpp.*\.(a|lib)'
            ),
            'not_match': re.compile(
                r'rm -f|vcxproj|'
                r'^\[\d+/\d+].*|'
                r'^Removing.*|'
                r'cmake.exe -E rm -f'
            ),
            'joins': re.compile(
                r'^-o|-MF|'
                r'^[-/]D |'
                r'^-arch|^-framework|^-isysroot|^-install_name'
            ),
            'ignore': re.compile(r'^--$'),
            'command_types': {
                'compile': re.compile(
                    r'(^|\b|[\'"]|[\\/])((x86_64-w64-mingw32-)?(g\+\+|c\+\+)(\.exe)?|clang(\+\+|-cl)|cl|em\+\+)(?:\.exe)?\b'),
                'link': re.compile(
                    r'(^|\b|[\'"]|[\\/])((x86_64-w64-mingw32-)?(g\+\+|c\+\+)(\.exe)?|clang(\+\+|-cl)|link)(\.exe)?\b.*\.(so|dll|a|lib)'),
                'archive': re.compile(r'(^|\b|[\'"]|[\\/])(lib|ar|llvm-ar|emar|gcc-ar)(?:\.exe)?\b')
            },
        }

        self.categories = {
            'includes': re.compile(r'^(/I|-I)'),
            'defines': re.compile(r'^(/D|-D)'),
            'optimization': re.compile(r'^(/O|-O|Ob)'),
            'debug': re.compile(r'^(/Zi|/FS|-g\d?|-gdwarf-4)'),
            'warnings': re.compile(r'^(/W|-W|/wd\d)|/external:W\d'),
            'codegen': re.compile(r'^([/-]std[:=]([^;]*)\b|-f|/EH[ascr]+|/RTC[1csu]+)'),
            'output': re.compile(r'^(/Fo|/Fd|/OUT:|-o)'),
            'defaults': re.compile(r'^(/nologo|/utf-8|/GR)'),
            'ignored': re.compile(
                r'^[-/](MD|MT|MF|c|TP)|'
                r'-lkernel32|-luser32|-lgdi32|-lwinspool|-lshell32|-lole32|-loleaut32|-luuid|-lcomdlg32|-ladvapi32'
            ),
            'emscripten': re.compile(r'^-s(SIDE_MODULE|SUPPORT_LONGJMP|USE_PTHREADS)'),
            'other': re.compile(r'.*')  # Catch-all
        }

        self.sourcedir = ''
        self.builddir = ''

    def get_command_type(self, command: str) -> Optional[str]:
        """Determine the command type (compile, link, archive)."""
        for cmd_type, pattern in self.config['command_types'].items():
            if pattern.search(command):
                return cmd_type
        return None

    def clean_token(self, token: str) -> str:
        """Apply erase patterns to a single token."""
        if token.startswith('--target='):
            return '--target=<arch>'
        if token.startswith('--gcc-toolchain='):
            return '--gcc-toolchain=<path>'
        if token.startswith('--sysroot='):
            return '--sysroot=<path>'
        if os.path.exists(token):
            token = os.path.normpath(token)
            # Normalize gen\include paths by removing builddir prefix
            if 'gen\\include' in token.replace('/', '\\'):
                token = token[len(os.path.commonprefix([self.builddir, token]))+1:] if self.builddir in token else token
                token = os.path.join('gen', 'include') if 'gen\\include' in token.replace('/', '\\') else token
            elif self.sourcedir in token:
                token = token[len(os.path.commonprefix([self.sourcedir, token]))+1:]
        return token

    def categorize_token(self, token: str) -> str:
        """Classify a token into a flag category."""
        for category, pattern in self.categories.items():
            if pattern.search(token):
                return category
        return 'other'

    def process_tokens(self, tokens: List[str]) -> Dict[str, List[str]]:
        """Clean, filter, and categorize tokens."""
        categorized = {'executable': [], 'source': []}
        categorized['executable'].append(os.path.normpath(tokens[0]))
        cleaned_tokens = [self.clean_token(token) for token in tokens[1:] if token]

        joined_tokens = []
        i: int = 0
        while i < len(cleaned_tokens):
            token = cleaned_tokens[i]
            if self.config['joins'].search(token) and i + 1 < len(cleaned_tokens):
                joined_token = f"{token} {cleaned_tokens[i + 1]}"
                joined_tokens.append(joined_token)
                i += 2
            else:
                joined_tokens.append(token)
                i += 1

        filtered_tokens = [
            token for token in joined_tokens
            if token and not self.config['ignore'].search(token)
        ]

        for token in filtered_tokens:
            if self.config['ignore'].search(token):
                continue
            category = self.categorize_token(token)
            if category not in categorized:
                categorized[category] = []
            match category:
                case 'other':
                    pass
                case 'defines':
                    categorized[category].append(token[2:])
                    continue
                case 'includes':
                    categorized[category].append(self.clean_token(token[2:]))
                    continue
                case 'codegen':
                    std_match = r'[/-]std[:=]([^;]*)\b'
                    std_lang = re.sub(std_match, r'std=\1', token)
                    if std_lang:
                        categorized[category].append(std_lang)
                    else:
                        categorized[category].append(token)
                    continue
                case _:
                    categorized[category].append(token)
                    continue

            if not token.startswith(('-', '/')):
                categorized['source'].append(token)
                continue
            categorized[category].append(token)

        for category in categorized:
            categorized[category].sort()
        return categorized

    def process(self, files: List[str], is_json: bool = True, filter_regex: Optional[str] = None) -> Tuple[Dict[str, SimpleNamespace], Dict[str, Dict[str, List[str]]]]:
        """Process the files and return results and all_flags."""
        if is_json:
            results = self.clean_commands(files)
        else:
            results = self.clean_build_log(files)

        # Filter results based on config['name'] matching the regex
        if filter_regex:
            try:
                pattern = re.compile(filter_regex)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
            results = {
                file: entry
                for file, entry in results.items()
                if pattern.search(entry.config.name)
            }

        if not results:
            print("No configurations matched the filter.")
            return {}, {}

        # Collect all flags for glossary
        all_flags = {}
        for file, entry in results.items():
            for cmd_type, categorized in entry.commands.items():
                if cmd_type not in all_flags:
                    all_flags[cmd_type] = {}
                for category, tokens in categorized.items():
                    if category in ['output', 'includes', 'source', 'executable']: continue
                    if category not in all_flags[cmd_type]:
                        all_flags[cmd_type][category] = []
                    all_flags[cmd_type][category].extend(tokens)

        return results, all_flags


    def clean_commands(self, json_files: List[str]) -> Dict[str, SimpleNamespace]:
        """Process multiple compile_commands.json files and return one command per type per file."""
        results = {}
        for json_file in json_files:
            compile_commands = load_json(json_file)
            processed_types: Set[str] = set()
            commands_by_type: Dict[str, Dict[str, List[str]]] = {}
            config = None

            for entry in compile_commands:
                command = entry['command']
                cmd_type = self.get_command_type(command)
                if not cmd_type or cmd_type in processed_types:
                    continue

                file_path = os.path.normpath(entry['file'])
                directory = os.path.normpath(entry['directory'])
                self.sourcedir = os.path.commonpath([directory, file_path])
                self.builddir = directory

                if config is None:
                    config = extract_config(self.sourcedir, self.builddir, command)

                categorized_tokens = self.process_tokens(split_command(command))
                if not any(categorized_tokens.values()):
                    print(f"Debug: No valid tokens after processing: {command[:50]}...")
                    continue

                commands_by_type[cmd_type] = categorized_tokens
                processed_types.add(cmd_type)

            if commands_by_type:
                results[json_file] = SimpleNamespace(config=config or SimpleNamespace(name='Unknown'), commands=commands_by_type)

        return results

    def clean_build_log(self, log_files: List[str]) -> Dict[str, SimpleNamespace]:
        """Process multiple build log files and return one command per type per file."""
        results = {}
        for log_file in log_files:
            compile_commands = parse_build_log(log_file)
            entries = self.clean_commands_from_entries(compile_commands, log_file)
            if entries:
                results[log_file] = entries[0]  # Only one entry per log file
        return results

    def clean_commands_from_entries(self, compile_commands: List[Dict], fallback_name: str = '') -> List[SimpleNamespace]:
        """Helper to process commands from JSON or log entries."""
        processed_types: Set[str] = set()
        commands_by_type: Dict[str, Dict[str, List[str]]] = {}
        config = SimpleNamespace(name=fallback_name or 'Unknown')

        for entry in compile_commands:
            command = entry['command']
            file = entry.get('file', '')
            if not self.config['line_match'].search(command + ' ' + file):
                continue
            if self.config['not_match'].search(command):
                continue

            cmd_type = self.get_command_type(command)
            if not cmd_type or cmd_type in processed_types:
                continue

            tokens = split_command(command)
            categorized_tokens = self.process_tokens(tokens)
            if not any(categorized_tokens.values()):
                continue

            commands_by_type[cmd_type] = categorized_tokens
            processed_types.add(cmd_type)

        if commands_by_type:
            return [SimpleNamespace(config=config, commands=commands_by_type)]
        return []

    def display_configs(self, results: Dict[str, SimpleNamespace], selected_categories: Optional[List[str]] = None):
        """Display the parsed configurations, filtered by selected categories."""
        available_categories = set(self.categories.keys())
        categories_to_show = available_categories if selected_categories is None else set(selected_categories) & available_categories

        for file, entry in results.items():
            print()
            fmt.s1(file)
            fmt.h(f"Config: {entry.config.name}", level=1)
            for cmd_type, categorized in entry.commands.items():
                if not any(categorized.values()):
                    continue
                fmt.h(f"{cmd_type.capitalize()}", level=1)
                for category, tokens in categorized.items():
                    if category not in categories_to_show or not tokens:
                        continue
                    fmt.h(category.capitalize(), level=2)
                    for token in tokens:
                        fmt.h(token, level=3)


    def display_table_comparison(self, results: Dict[str, SimpleNamespace], selected_categories: Optional[List[str]] = None):
        """Display a table for side-by-side comparison of flags across builds, filtered by selected categories."""
        console = Console()
        skip_these = ['output', 'ignored', 'defaults', 'source', 'executable']
        available_categories = set(self.categories.keys())
        categories_to_show = available_categories if selected_categories is None else set(selected_categories) & available_categories

        all_data = {}
        for file, entry in results.items():
            commands = entry.commands
            for cmd_type, categorized in commands.items():
                if cmd_type not in all_data:
                    all_data[cmd_type] = {}
                for category, tokens in categorized.items():
                    if category in skip_these or category not in categories_to_show:
                        continue
                    if category not in all_data[cmd_type]:
                        all_data[cmd_type][category] = {}
                    for token in tokens:
                        if token not in all_data[cmd_type][category]:
                            all_data[cmd_type][category][token] = []
                        all_data[cmd_type][category][token].append(file)

        for cmd_type, categories in all_data.items():
            if len(categories) == 0:
                continue
            fmt.t2(f"Comparison Table for {cmd_type.capitalize()}")
            for category, flags in categories.items():
                table = Table(title=category.capitalize(), show_header=True, header_style="bold magenta")
                table.add_column("Flag", no_wrap=True)
                for file in results.keys():
                    header = results[file].config.name
                    table.add_column(header, style="cyan", overflow='fold')

                row_index = 0
                for flag in sorted(flags.keys()):
                    row = [flag]
                    for file in results.keys():
                        if file in flags[flag]:
                            row.append("Yes")
                        else:
                            row.append("")
                    row_style = "on #333333" if row_index % 2 == 0 else None
                    table.add_row(*row, style=row_style)
                    row_index += 1
                console.print(table)


def main():
    cleaner = CompileCommandsCleaner()
    available_categories = cleaner.categories.keys()

    parser = argparse.ArgumentParser(
        description="Clean compile_commands.json or build log files to extract one command per type with categorized flags.",
        formatter_class=RawTextHelpFormatter
    )
    parser.add_argument('files', nargs='*', default=None, help="Paths to compile_commands.json or build log files (space-separated or individual)")
    parser.add_argument('--json', action='store_true', help="Process as JSON files (default)")
    parser.add_argument('--log', action='store_true', help="Process as build log files")
    parser.add_argument('--filter', default=None, help="Regex pattern to filter configurations based on config name")
    parser.add_argument('--hide-configs', action='store_true', help="Hide the list of configs")
    parser.add_argument('--hide-table', action='store_true', help="Hide the table of options")
    parser.add_argument('--hide-glossary', action='store_true', help="Hide the glossary of flags")
    parser.add_argument('--categories', default=None, help=f"""Comma-separated list of categories to display (default: all).\nAvailable categories:\n\t{'\n\t'.join(available_categories)}""")

    args = parser.parse_args()

    glossary = load_glossary_config()

    if not args.json and not args.log:
        args.json = True  # Default to JSON

    file_list = []
    if args.files:
        if len(args.files) == 1:
            file_list = args.files[0].split()
        else:
            file_list = args.files

    for file in file_list:
        if not os.path.exists(file):
            raise FileNotFoundError(f"Error: File {file} does not exist")

    if not file_list:
        parser.error("No valid files provided")

        # Process categories argument
    selected_categories = None
    if args.categories:
        selected_categories = [cat.strip() for cat in args.categories.split(',')]
        invalid_categories = set(selected_categories) - available_categories
        if invalid_categories:
            parser.error(f"Invalid categories: {', '.join(invalid_categories)}. Available categories: {', '.join(available_categories)}")

    fmt.t2("Cleaned Build Commands")
    results, all_flags = cleaner.process(file_list, is_json=args.json, filter_regex=args.filter)
    if not results:
        return

    if not args.hide_configs:
        cleaner.display_configs(results)

    if not args.hide_glossary:
        display_glossary( glossary, all_flags)

    if not args.hide_table:
        cleaner.display_table_comparison(results, selected_categories)


if __name__ == "__main__":
    main()