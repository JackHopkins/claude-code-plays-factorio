#!/usr/bin/env python3
# view-claude.py - Process Claude Code output with proper formatting and syntax highlighting

import subprocess
import sys
import re
import argparse
from datetime import datetime

# Try to import pygments for syntax highlighting
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer, guess_lexer
    from pygments.formatters import TerminalFormatter, Terminal256Formatter

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False



def get_tmux_content(session="claude-code", with_colors=True, escape_mode='raw'):
    """Capture tmux pane content"""
    cmd = ["tmux", "capture-pane", "-t", session, "-p", "-S", "-"]
    if with_colors:
        cmd.append("-e")  # Get colors

    try:
        result = subprocess.run(cmd, capture_output=True, text=False)
        raw_bytes = result.stdout
        content = raw_bytes.decode('utf-8', errors='replace')

        # Return both colored and stripped versions
        if with_colors:
            return content, strip_ansi_codes(content)
        else:
            return content, content

    except subprocess.CalledProcessError as e:
        print(f"Error capturing tmux session: {e}", file=sys.stderr)
        return "", ""


def find_code_blocks(content):
    """Find all code blocks by properly parsing parentheses"""
    blocks = []

    # Find all potential starts of code blocks
    pattern = r'execute \(MCP\)\(code:\s*"'

    pos = 0
    while True:
        match = re.search(pattern, content[pos:])
        if not match:
            break

        start = pos + match.start()
        code_start = pos + match.end()

        # Now find the matching ") that closes this code block
        # We need to handle escaped quotes and find the actual end
        i = code_start
        escape_next = False

        while i < len(content):
            char = content[i]

            if escape_next:
                escape_next = False
                i += 1
                continue

            if char == '\\':
                # Check if this is an escape sequence like \n or an escaped backslash
                if i + 1 < len(content) and content[i + 1] in 'ntr"\\':
                    i += 2  # Skip the escape sequence
                    continue
                else:
                    escape_next = True
                    i += 1
                    continue

            if char == '"' and i + 1 < len(content) and content[i + 1] == ')':
                # Found the end of the code block
                code = content[code_start:i]
                blocks.append({
                    'full_match': content[start:i + 2],
                    'prefix': content[start:code_start],
                    'code': code,
                    'start': start,
                    'end': i + 2
                })
                pos = i + 2
                break

            i += 1
        else:
            # No matching end found, move past this match
            pos = start + len(match.group())

    return blocks


def clean_code(code):
    """Clean up code by removing wrapping artifacts and converting escape sequences"""
    # Temporarily replace literal escape sequences
    code = code.replace('\\n', '<<<ESCAPED_NEWLINE>>>')
    code = code.replace('\\t', '<<<ESCAPED_TAB>>>')
    code = code.replace('\\r', '<<<ESCAPED_RETURN>>>')

    # Remove wrapping artifacts (actual newlines with spaces)
    mcp_name_len = "                              "
    code = code.replace('\n', "")
    code = code.replace(mcp_name_len, "")
    #code = re.sub(r'\n\s{'+mcp_name_len+'}', '', code)

    # Convert placeholders to actual characters
    code = code.replace('<<<ESCAPED_NEWLINE>>>', '\n')
    code = code.replace('<<<ESCAPED_TAB>>>', '\t')
    code = code.replace('<<<ESCAPED_RETURN>>>', '\r')

    return code


# def highlight_code(code, language='python'):
#     """Apply syntax highlighting to code if pygments is available"""
#     if not PYGMENTS_AVAILABLE:
#         return code
#
#     try:
#         if language == 'python':
#             lexer = PythonLexer()
#         else:
#             lexer = guess_lexer(code)
#
#         # Use 256 color terminal formatter for better colors
#         formatter = Terminal256Formatter(style='monokai')
#         return highlight(code, lexer, formatter).rstrip()
#     except:
#         # If highlighting fails, return the original code
#         return code


def process_code_blocks(colored_content, clean_content, use_highlighting=True, use_formatting=True):
    """Process content to fix wrapped code blocks with optional syntax highlighting and auto-formatting

    Args:
        colored_content: The original content with ANSI color codes
        clean_content: The content with ANSI codes stripped for regex matching
        use_highlighting: Whether to apply syntax highlighting to code blocks
        use_formatting: Whether to auto-format code blocks
    """
    # Find code blocks in the clean content (no ANSI codes)
    blocks = find_code_blocks(clean_content)

    if not blocks:
        # No code blocks found, return original colored content
        return colored_content

    # Build a mapping between clean and colored content positions
    # This is needed to accurately replace blocks in the colored version
    position_map = build_position_map(colored_content, clean_content)

    # Process from end to start to maintain positions
    result = colored_content
    for block in reversed(blocks):
        code = clean_code(block['code'])
        code = code.replace('\\\"', "\"")

        # Auto-format the code if requested
        if use_formatting:
            code = format_code(code)

        #code = code.replace(' \t', ' ')

        if use_highlighting:
            # Apply enhanced syntax highlighting
            highlighted_code = highlight_code(code)
            # Indent each line
            indented_code = '\n\t\t'.join(highlighted_code.split('\n'))
        else:
            # Just indent without highlighting
            indented_code = '\n\t\t'.join(code.split('\n'))

        # Map clean content positions to colored content positions
        colored_start = position_map[block['start']]
        colored_end = position_map[block['end']]

        # Extract the prefix from the colored content to preserve any colors
        colored_prefix = result[colored_start:colored_start + len(block['prefix'])]

        # Build the new block
        new_block = f"{colored_prefix}\n\t\t{indented_code}\"\n)"

        # Replace in the colored content
        result = result[:colored_start] + new_block + result[colored_end:]


        BOTTOM_MATTER = "@anthropic-ai/claude-code"
        result = result.replace(BOTTOM_MATTER, "@claude-code x @factorio-learning-environment")

    return result


def format_code(code, language='python'):
    """Auto-format code with proper line breaks and indentation"""

    # Try different formatters in order of preference
    formatted = None

    # Try black first (most popular Python formatter)
    if not formatted:
        formatted = format_with_black(code)

    # Try autopep8 as fallback
    if not formatted:
        formatted = format_with_autopep8(code)

    # Try yapf as another fallback
    if not formatted:
        formatted = format_with_yapf(code)

    # If no formatter worked, at least fix basic formatting
    if not formatted:
        formatted = basic_format(code)

    return formatted


def format_with_black(code):
    """Format Python code with black"""
    try:
        import black

        try:
            # Format with black
            formatted = black.format_str(
                code,
                mode=black.Mode(
                    line_length=88,  # Black's default
                    string_normalization=True,
                    is_pyi=False,
                    is_ipynb=False,
                    magic_trailing_comma=True,
                    #experimental_string_processing=False,
                    target_versions={black.TargetVersion.PY38},
                )
            )
            #diff = black.diff(a_name=formatted, b_name=code)
            return formatted.rstrip()

        except black.InvalidInput as e :

            # If black can't parse it, return None
            return None

    except ImportError as e:
        return None
    except Exception as e:
        #print(f"Black formatting error: {e}", file=sys.stderr)
        return None


def format_with_autopep8(code):
    """Format Python code with autopep8"""
    try:
        import autopep8

        formatted = autopep8.fix_code(
            code,
            options={
                'aggressive': 1,  # Level of aggressiveness
                'max_line_length': 88,
                'indent_size': 4,
            }
        )
        return formatted.rstrip()

    except ImportError:
        return None
    except Exception as e:
        print(f"Autopep8 formatting error: {e}", file=sys.stderr)
        return None


def format_with_yapf(code):
    """Format Python code with yapf"""
    try:
        from yapf.yapflib.yapf_api import FormatCode

        formatted, _ = FormatCode(
            code,
            style_config={
                'based_on_style': 'pep8',
                'column_limit': 88,
                'indent_width': 4,
            }
        )
        return formatted.rstrip()

    except ImportError:
        return None
    except Exception as e:
        print(f"YAPF formatting error: {e}", file=sys.stderr)
        return None


def basic_format(code):
    """Basic formatting when no proper formatter is available"""
    import re

    # Remove excess whitespace
    code = code.strip()

    # Fix common issues
    lines = code.split('\n')
    formatted_lines = []
    indent_level = 0

    for line in lines:
        stripped = line.strip()

        if not stripped:
            formatted_lines.append('')
            continue

        # Decrease indent for these keywords
        if stripped.startswith(('else:', 'elif ', 'except:', 'except ', 'finally:', ')', ']', '}')):
            indent_level = max(0, indent_level - 1)

        # Add the line with current indent
        formatted_lines.append('    ' * indent_level + stripped)

        # Increase indent after these patterns
        if stripped.endswith(':') or stripped.endswith('(') or stripped.endswith('[') or stripped.endswith('{'):
            indent_level += 1

        # Handle line continuations
        if stripped.endswith('\\'):
            indent_level += 1
        elif indent_level > 0 and not stripped.endswith((':', '(', '[', '{', '\\')):
            # Check if we should decrease indent (rough heuristic)
            if not any(stripped.startswith(kw) for kw in ['if ', 'for ', 'while ', 'def ', 'class ', 'with ', 'try:']):
                indent_level = max(0, indent_level - 1)

    return '\n'.join(formatted_lines)


def highlight_code(code, language='python'):
    """Apply enhanced syntax highlighting with better color scheme"""
    if not PYGMENTS_AVAILABLE:
        return code

    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, guess_lexer, PythonLexer
        from pygments.formatters import Terminal256Formatter
        from pygments.styles import get_style_by_name

        # Try to detect language more intelligently
        if language == 'python' or 'import ' in code or 'def ' in code or 'class ' in code:
            lexer = PythonLexer()
        else:
            try:
                lexer = guess_lexer(code)
            except:
                lexer = get_lexer_by_name('text')

        # Use a richer color scheme
        # Good options: 'monokai', 'native', 'fruity', 'vim', 'paraiso-dark', 'material'
        formatter = Terminal256Formatter(
            style='monokai',
            # Enable full color range
            full=True,
        )

        highlighted = highlight(code, lexer, formatter).rstrip()

        # Post-process to enhance certain patterns
        highlighted = enhance_patterns(highlighted)

        return highlighted

    except Exception as e:
        print(f"Highlighting failed: {e}", file=sys.stderr)
        return code


def enhance_patterns(highlighted_code):
    """Post-process highlighted code to enhance certain patterns"""
    import re

    # Make TODO/FIXME/NOTE comments stand out more
    todo_pattern = r'(#\s*(TODO|FIXME|NOTE|HACK|WARNING):.*$)'
    highlighted_code = re.sub(
        todo_pattern,
        '\033[43m\033[30m\\1\033[0m',  # Yellow background, black text
        highlighted_code,
        flags=re.MULTILINE
    )

    # Make function definitions more prominent (if not already highlighted well)
    # This is optional and depends on your preference
    func_pattern = r'(\bdef\s+\w+)'
    highlighted_code = re.sub(
        func_pattern,
        '\033[1m\\1\033[0m',  # Bold
        highlighted_code
    )

    return highlighted_code


# Installation helper
def check_formatters():
    """Check which formatters are available and suggest installations"""
    formatters = {
        'black': 'pip install black',
        'autopep8': 'pip install autopep8',
        'yapf': 'pip install yapf',
        'pygments': 'pip install pygments>=2.17.0'
    }

    available = []
    missing = []

    for formatter in formatters:
        try:
            __import__(formatter)
            available.append(formatter)
        except ImportError:
            missing.append(formatter)

    if missing:
        print("For better code formatting, install:")
        for fmt in missing:
            print(f"  {formatters[fmt]}")

    return available

def build_position_map(colored_content, clean_content):
    """Build a mapping between positions in clean and colored content

    This maps each position in clean_content to the corresponding position
    in colored_content, accounting for ANSI escape sequences.
    """
    position_map = {}
    colored_pos = 0
    clean_pos = 0

    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    while clean_pos < len(clean_content) and colored_pos < len(colored_content):
        # Check if we're at the start of an ANSI sequence in colored content
        ansi_match = ansi_escape.match(colored_content, colored_pos)

        if ansi_match:
            # Skip over the ANSI sequence in colored content
            colored_pos = ansi_match.end()
        else:
            # Map the position
            position_map[clean_pos] = colored_pos

            # Verify characters match (for debugging)
            if colored_content[colored_pos] != clean_content[clean_pos]:
                # Characters should match when not in ANSI sequence
                # This is a sanity check
                pass

            colored_pos += 1
            clean_pos += 1

    # Map the final position (end of content)
    position_map[clean_pos] = colored_pos

    return position_map

def strip_ansi_codes(text):
    """Remove ANSI color codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def extract_code_blocks(content):
    """Extract just the code from execute blocks"""
    blocks = find_code_blocks(content)

    code_blocks = []
    for block in blocks:
        code = clean_code(block['code'])
        code_blocks.append(code)

    return code_blocks


def pretty_print(content, use_highlighting=True):
    """Pretty print with formatted code blocks"""
    print("═" * 60)
    print("         Claude Code Output (Formatted)")
    print("═" * 60)
    print()

    code_blocks = extract_code_blocks(content)

    if not code_blocks:
        print("No code blocks found")
        return

    for i, code in enumerate(code_blocks, 1):
        print(f"┌─── Code Block {i} {'─' * (45 - len(str(i)))}")
        print("│")

        if use_highlighting and PYGMENTS_AVAILABLE:
            highlighted = highlight_code(code)
            for line in highlighted.split('\n'):
                print(f"│ {line}")
        else:
            for line in code.split('\n'):
                print(f"│ {line}")

        print("│")
        print(f"└{'─' * 55}")
        print()


def code_only_mode(content, use_highlighting=True):
    """Display only the code blocks, cleanly formatted"""
    code_blocks = extract_code_blocks(content)

    for i, code in enumerate(code_blocks, 1):
        print(f"### Code Block {i} ###")
        if use_highlighting and PYGMENTS_AVAILABLE:
            print(highlight_code(code))
        else:
            print(code)
        print()


def stream_mode(args):
    import time
    import sys
    import os
    import signal

    # Configuration for refresh behavior
    FULL_REFRESH_INTERVAL = 10  # Do a full screen clear every N updates
    MAX_CONTENT_SIZE = 1000000  # Force refresh if content exceeds this size
    update_counter = 0
    last_content_hash = None

    def cleanup_terminal():
        """Restore terminal state"""
        print('\033[?25h', end='')  # Show cursor
        sys.stdout.flush()

    def handle_sigwinch(signum, frame):
        """Handle terminal resize"""
        nonlocal update_counter
        update_counter = FULL_REFRESH_INTERVAL - 1  # Force refresh on next update

    try:
        # Set up signal handler for terminal resize
        if hasattr(signal, 'SIGWINCH'):
            signal.signal(signal.SIGWINCH, handle_sigwinch)

        # Hide cursor for cleaner display
        print('\033[?25l', end='')

        # Initial clear
        os.system('clear' if os.name == 'posix' else 'cls')

        while True:
            update_counter += 1

            # Get current terminal size for smarter refresh decisions
            try:
                terminal_size = os.get_terminal_size()
                terminal_changed = False
            except:
                terminal_size = None
                terminal_changed = False

            colored_content, clean_content = get_tmux_content(with_colors=True)

            # Calculate a simple hash to detect major content changes
            content_hash = hash(clean_content[:1000])  # Hash first 1000 chars for efficiency
            content_significantly_changed = (
                    last_content_hash is not None and
                    abs(content_hash - last_content_hash) > 1000000000
            )
            last_content_hash = content_hash

            # Determine if we need a full refresh
            needs_full_refresh = (
                    update_counter % FULL_REFRESH_INTERVAL == 0 or
                    len(clean_content) > MAX_CONTENT_SIZE or
                    content_significantly_changed or
                    terminal_changed
            )

            if needs_full_refresh:
                # Do a full screen clear
                os.system('clear' if os.name == 'posix' else 'cls')
                update_counter = 0  # Reset counter
            else:
                # Regular cursor-based update
                print('\033[H', end='')

            # Process and display content
            try:
                processed = process_code_blocks(
                    colored_content,
                    clean_content,
                    use_highlighting=args.highlight,
                    use_formatting=getattr(args, 'formatting', True)
                )

                # If content is very long, truncate with a notice
                # if terminal_size and len(processed.split('\n')) > terminal_size.lines * 3:
                #     lines = processed.split('\n')
                #     visible_lines = terminal_size.lines - 2
                #     processed += f"\n[... Content truncated. Showing {visible_lines} of {len(lines)} lines ...]"
                #     processed = '\n'.join(lines[-visible_lines:])

                # Clear from cursor to end of screen and print
                print(processed + '\033[J', end='')

            except Exception as e:
                # If processing fails, show raw content as fallback
                print(f"Processing error: {e}\n", file=sys.stderr)
                print(colored_content + '\033[J', end='')

            sys.stdout.flush()
            time.sleep(args.interval)

    except KeyboardInterrupt:
        cleanup_terminal()
        os.system('clear' if os.name == 'posix' else 'cls')
        print("\nStopped streaming")
    except Exception as e:
        cleanup_terminal()
        print(f"\nError in stream mode: {e}", file=sys.stderr)
        raise
    finally:
        # Always restore cursor visibility
        cleanup_terminal()

def follow_mode(args):
    """Follow new output only"""
    import time
    import os

    last_content = ""
    try:
        while True:
            colored_content, clean_content = get_tmux_content(with_colors=True)
            if clean_content != last_content:
                os.system('clear' if os.name == 'posix' else 'cls')
                processed = process_code_blocks(colored_content, clean_content, use_highlighting=args.highlight)
                print(processed)
                last_content = clean_content
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped following")


def main():
    parser = argparse.ArgumentParser(description='Process Claude Code output')
    parser.add_argument('mode', nargs='?', default='view',
                        choices=['view', 'pretty', 'code', 'stream', 'follow', 'save'],
                        help='Display mode')
    parser.add_argument('-s', '--session', default='claude-code',
                        help='Tmux session name')
    parser.add_argument('-o', '--output', help='Output file for save mode')
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                        help='Refresh interval for stream mode')
    parser.add_argument('--no-colors', dest='colors', action='store_false',
                        help='Disable ANSI colors')
    parser.add_argument('--no-highlight', dest='highlight', action='store_false',
                        help='Disable syntax highlighting')

    args = parser.parse_args()
    args.highlight = True
    args.mode = 'stream'

    if not PYGMENTS_AVAILABLE and args.highlight:
        print("Note: Install pygments for syntax highlighting: pip install pygments", file=sys.stderr)

    if args.mode == 'stream':
        stream_mode(args)
    elif args.mode == 'follow':
        follow_mode(args)
    else:
        # Get content once
        content = get_tmux_content(session=args.session, with_colors=args.colors)

        if args.mode == 'view':
            processed = process_code_blocks(content, use_highlighting=args.highlight)
            print(processed)
        elif args.mode == 'pretty':
            pretty_print(content, use_highlighting=args.highlight)
        elif args.mode == 'code':
            code_only_mode(content, use_highlighting=args.highlight)
        elif args.mode == 'save':
            # For save mode, typically don't use highlighting (plain text)
            processed = process_code_blocks(content, use_highlighting=False)
            output_file = args.output or f"claude-output-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
            with open(output_file, 'w') as f:
                f.write(processed)
            print(f"Saved to {output_file}")

if __name__ == "__main__":
    main()