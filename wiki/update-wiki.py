# -*- coding: utf-8 -*-
"""Python implementation of old ``update-wiki.sh`` merged with ``process.py``.

*From ``update-wiki.sh``*

This script calls git heavily to:
1. Takes the content from this repo;
2. Then writes it into a local clone of https://github.com/nerdvegas/rez.wiki.git;
3. Then follows the procedure outlined in README from 2.

This process exists because GitHub does not support contributions to wiki
repositories - this is a workaround.

See Also:
    Original wiki update script files:

    - ``wiki/update-wiki.sh`` at rez 2.50.0, which calls
    - ``utils/process.py`` from nerdvegas/rez.wiki at d632328, and
    - ``utils/update.sh`` from nerdvegas/rez.wiki at d632328
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
from collections import defaultdict
import errno
from io import open
import os
import re
import subprocess
import shutil
import sys


# py3.7+ only
if sys.version_info[:2] < (3, 7):
    print("update-wiki.py: ust use python-3.7 or greater", file=sys.stderr)
    sys.exit(1)


THIS_FILE = os.path.abspath(__file__)
THIS_DIR = os.path.dirname(THIS_FILE)
REZ_SOURCE_DIR = os.getenv("REZ_SOURCE_DIR", os.path.dirname(THIS_DIR))

OUT_DIR = "out"
GITHUB_RELEASE = "unknown-release"
GITHUB_REPO = "unknown/rez"
GITHUB_BRANCH = "master"
GITHUB_WORKFLOW = "Wiki"
CLONE_URL = None


def add_toc(txt):
    """Add github-style ToC to start of md content.
    """
    lines = txt.split('\n')
    toc_lines = []
    mindepth = None

    for line in lines:
        if not line.startswith('#'):
            continue

        parts = line.split()

        hashblock = parts[0]
        if set(hashblock) != set(["#"]):
            continue

        depth = len(hashblock)
        if mindepth is None:
            mindepth = depth
        depth -= mindepth

        toc_lines.append("%s- [%s](#%s)" % (
            ' ' * 4 * depth,
            ' '.join(parts[1:]),
            '-'.join(x.lower() for x in parts[1:])
        ))

    if not toc_lines:
        return txt

    return '\n'.join(toc_lines) + "\n\n" + txt


def creating_configuring_rez_md(txt):
    lines = txt.split('\n')

    start = None
    end = None
    for i, line in enumerate(lines):
        if "__DOC_START__" in line:
            start = i
        elif "__DOC_END__" in line:
            end = i

    lines = lines[start:end + 1]
    assign_regex = re.compile("^([a-z0-9_]+) =")
    settings = {}

    # parse out settings and their comment
    for i, line in enumerate(lines):
        m = assign_regex.match(line)
        if not m:
            continue

        start_defn = i
        end_defn = i
        while lines[end_defn].strip() and not lines[end_defn].startswith('#'):
            end_defn += 1

        defn_lines = lines[start_defn:end_defn]
        defn_lines = [("    " + x) for x in defn_lines]  # turn into code block
        defn = '\n'.join(defn_lines)

        end_comment = i
        while not lines[end_comment].startswith('#'):
            end_comment -= 1

        start_comment = end_comment
        while lines[start_comment].startswith('#'):
            start_comment -= 1
        start_comment += 1

        comments = lines[start_comment:end_comment + 1]
        comments = [x[2:] for x in comments]  # drop leading '# '
        comment = '\n'.join(comments)

        varname = m.groups()[0]
        settings[varname] = (defn, comment)

    # generate md text
    md = []

    for varname, (defn, comment) in sorted(settings.items()):
        md.append("### %s" % varname)
        md.append("")
        md.append(defn)
        md.append("")
        md.append(comment)
        md.append("")

    md = '\n'.join(md)
    return md


def create_contributors_md(src_path):
    # Make sure aliases KEY is fully lowercase to match correctly!
    aliases = {
        "allan.johns": "Allan Johns",
        "allan johns": "Allan Johns",
        "ajohns": "Allan Johns",
        "nerdvegas": "Allan Johns",
        "nerdvegas@gmail.com": "Allan Johns",
        "method": "Allan Johns",
        "rachel johns": "Allan Johns",
        "root": "Allan Johns",
        "(no author)": "Allan Johns",

        "mylene pepe": "Mylene Pepe",
        "michael.morehouse": "Michael Morehouse",
        "phunter.nz": "Philip Hunter",
        "joe yu": "Joseph Yu",
        "j0yu": "Joseph Yu",
        "fpiparo": "Fabio Piparo"
    }
    out = subprocess.check_output(
        ["git", "shortlog", "-sn", "HEAD"],
        encoding="utf-8",
        cwd=src_path,
    )
    contributors = defaultdict(int)
    regex = re.compile(
        r'^\s*(?P<commits>\d+)\s+(?P<author>.+)\s*$',
        flags=re.MULTILINE | re.UNICODE
    )

    for match in regex.finditer(out):
        author = match.group('author')
        author_html = "%s<br>" % aliases.get(author.lower(), author)
        contributors[author_html] += int(match.group('commits'))

    return '\n'.join(
        author_html for author_html, commit_count in
        sorted(contributors.items(), key=lambda x: x[1], reverse=True)
    )


def process_markdown_files():
    no_toc = [
        "Credits.md",
        "Command-Line-Tools.md",
        "Home.md",
        "_Footer.md",
        "_Sidebar.md",
    ]

    pagespath = os.path.join(THIS_DIR, "pages")

    src_path = os.getenv("REZ_SOURCE_DIR")
    if src_path is None:
        print(
            "Must provide REZ_SOURCE_DIR which points at root of "
            "rez source clone", file=sys.stderr,
        )
        sys.exit(1)

    def do_replace(filename, token_md):
        srcfile = os.path.join(pagespath, "_%s.md" % filename)
        destfile = os.path.join(OUT_DIR, "%s.md" % filename)

        with open(srcfile, encoding='utf-8') as f:
            txt = f.read()

        for token, md in token_md.items():
            txt = txt.replace(token, md)

        print("Writing ", destfile, "...", sep="")
        with open(destfile, 'w', encoding='utf-8') as f:
            f.write(txt)

    # generate markdown from rezconfig.py, add to _Configuring-Rez.md and write
    # out to Configuring-Rez.md
    filepath = os.path.join(src_path, "src", "rez", "rezconfig.py")
    with open(filepath) as f:
        txt = f.read()

    do_replace(
        "Configuring-Rez",
        {
            "__REZCONFIG_MD__": creating_configuring_rez_md(txt),
            "__GITHUB_REPO__": GITHUB_REPO,
        }
    )

    # generate markdown contributors list, add to _Credits.md and write out to
    # Credits.md
    md = create_contributors_md(src_path)
    do_replace("Credits", {"__CONTRIBUTORS_MD__": md})

    do_replace(
        "Command-Line-Tools",
        {
            "__GENERATED_MD__": create_clitools_markdown(src_path)
        }
    )

    do_replace("_Footer", {"__GITHUB_REPO__": GITHUB_REPO})

    try:
        from urllib import quote
    except ImportError:
        from urllib.parse import quote
    user, repo_name = GITHUB_REPO.split('/')
    do_replace(
        "_Sidebar",
        {
            "__GITHUB_RELEASE__": GITHUB_RELEASE,
            "__GITHUB_REPO__": GITHUB_REPO,
            "___GITHUB_USER___": user,
            "__REPO_NAME__": repo_name,
            "__WORKFLOW__": quote(GITHUB_WORKFLOW, safe=""),
            "__BRANCH__": quote(GITHUB_BRANCH, safe=""),
        }
    )

    # process each md file:
    # * adds TOC;
    # * replaces short-form content links like '[[here:Blah.md#Header]]' with full form;
    # * copies to the root dir.
    #
    skip_regex = r'^_(?!(Sidebar|Footer))|(?<!.md)$'
    for name in os.listdir(pagespath):
        if re.match(skip_regex, name):
            continue

        print("Processing ", name, "...", sep="")

        src = os.path.join(pagespath, name)
        dest = os.path.join(OUT_DIR, name)

        if name in no_toc:
            shutil.copyfile(src, dest)
            continue

        with open(src) as f:
            txt = f.read()

        content = add_toc(txt)
        with open(dest, 'w') as out:
            out.write(content)


################################################################################
# Command-Line-Tools.md functions and formatter classes
################################################################################

def create_clitools_markdown(src_path):
    """Generate the formatted markdown for each rez cli tool.

    Hot-import rez cli library to get parsers.

    Args:
        src_path (str): Full path to the rez source code repository.

    Returns:
        str: Generated markdown text.
    """
    sys.path.insert(0, os.path.join(src_path, "src"))
    try:
        from rez.cli._main import setup_parser
        from rez.cli._util import LazySubParsersAction

        main_parser = setup_parser()
        command_help = []
        parsers = [main_parser]
        for action in main_parser._actions:
            if isinstance(action, LazySubParsersAction):
                parsers += action.choices.values()

        for arg_parser in parsers:
            arg_parser.formatter_class = MarkdownHelpFormatter
            command_help.append(arg_parser.format_help())
    finally:
        sys.path.pop(0)

    return "\n\n\n".join(command_help)


class MarkdownHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):

    def _format_usage(self, usage, actions, groups, prefix):
        """Override to produce markdown title and code block formatting.

        Return:
            str: Markdown title and code block formatted usage.
        """
        prefix_was_none = prefix is None
        if prefix_was_none:
            prefix = "# {self._prog}\n```\n".format(self=self)

        super_format_usage = super(MarkdownHelpFormatter, self)._format_usage
        formatted_usage = super_format_usage(usage, actions, groups, prefix)

        if prefix_was_none:
            # Fix extra spaces calculated from old "usage: rez ..." prompt
            extra_spaces = "{newline:<{count}} ".format(
                newline="\n",
                count=len("usage: {self._prog}".format(self=self))
            )
            formatted_usage = formatted_usage[:-1] + "```\n"
            formatted_usage = formatted_usage.replace(extra_spaces, "\n")

        return formatted_usage

    def remap_heading(self, heading):
        """Remap argparse headings to shorter, markdown formatted headings.

        Args:
            heading (str): Original heading to remap and format.

        Returns:
            str: Remapped and formatted heading, if any.
        """
        if heading == "optional arguments":
            return "\n**Flags**\n"
        elif heading == "positional arguments":
            return "" if self._prog == "rez" else "\n**Arguments**\n"
        else:
            return heading

    def start_section(self, heading):
        """Extend to remap optional/positional arguments headings.

        Args:
            heading (str): Section heading to parse.
        """
        if self.remap_heading(heading) == heading:
            super(MarkdownHelpFormatter, self).start_section(heading)
        else:
            self._indent()
            self._add_item(self.remap_heading, [heading])
            super(MarkdownHelpFormatter, self).start_section(argparse.SUPPRESS)

    def _fill_text(self, text, width, indent):
        """No indent for description, keep subsequent indents.

        Return:
            str: Description but without leading indents.
        """
        super_fill_text = super(MarkdownHelpFormatter, self)._fill_text
        return super_fill_text(text, width, indent).lstrip()

    def _format_action(self, action):
        """Extend to format rez sub commands as table of links.

        Returns:
            str: Formatted help text for an action.
        """
        backup_width = self._width
        if self._prog == "rez" and action.nargs is None:
            self._width = 2000  # Temporary thicc width to avoid wrapping

        try:
            super_format = super(MarkdownHelpFormatter, self)._format_action
            help_text = super_format(action)
        finally:
            self._width = backup_width

        if self._prog == "rez":
            # Sub commands, format them with links
            if action.nargs is None:
                help_text = re.sub(
                    r'^\s+(\S+)(\s+)',
                    r'[\1](#rez-\1)\2| ',
                    help_text
                )

            # Sub commands heading, format as table heading
            elif action.metavar == "COMMAND":
                help_text = re.sub(
                    r'^\s+COMMAND',
                    "`COMMAND` | Description\n----|----",
                    help_text
                )

        return help_text


class UpdateWikiParser(argparse.ArgumentParser):
    """Parser flags, using global variables as defaults."""
    INIT_DEFAULTS = {
        "prog": "update-wiki",
        "description": "Update GitHub Wiki",
        "formatter_class": argparse.ArgumentDefaultsHelpFormatter,
    }

    def __init__(self, **kwargs):
        """Setup default arguments and parser description/program name.

        If no parser description/program name are given, default ones will
        be assigned.

        Args:
            kwargs (dict[str]):
                Same key word arguments taken by
                ``argparse.ArgumentParser.__init__()``
        """
        for key, value in self.INIT_DEFAULTS.items():
            kwargs.setdefault(key, value)
        super(UpdateWikiParser, self).__init__(**kwargs)

        self.add_argument(
            "--github-release",
            dest="release",
            default=GITHUB_RELEASE,
            help="GitHub release the wiki is generated from"
        )
        self.add_argument(
            "--github-repo",
            default=GITHUB_REPO,
            dest="repo",
            help="Url to GitHub repository without leading github.com/"
        )
        self.add_argument(
            "--github-branch",
            default=GITHUB_BRANCH,
            dest="branch",
            help="Name of git branch that is generating the Wiki"
        )
        self.add_argument(
            "--github-workflow",
            default=GITHUB_WORKFLOW,
            dest="workflow",
            help="Name of GitHub workflow that is generating the Wiki"
        )
        self.add_argument(
            "--wiki-url",
            default=CLONE_URL,
            dest="url",
            help="Use this url to git clone wiki from"
        )
        self.add_argument(
            "--out",
            default=OUT_DIR,
            dest="dir",
            help="Output dir"
        )


if __name__ == "__main__":
    # Quick check for "git" and throw meaningful error message
    try:
        subprocess.check_call(["git", "--version"])
    except OSError as error:
        if error.errno == errno.ENOENT:
            raise OSError(errno.ENOENT, '"git" needed but not found in PATH')
        raise

    args = UpdateWikiParser().parse_args()
    CLONE_URL = args.url
    GITHUB_RELEASE = args.release
    GITHUB_REPO = args.repo
    GITHUB_BRANCH = args.branch
    GITHUB_WORKFLOW = args.workflow
    OUT_DIR = os.path.abspath(args.dir)

    if not CLONE_URL:
        CLONE_URL = "git@github.com:%s.wiki.git" % GITHUB_REPO

    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    subprocess.check_call(
        ["git", "clone", "--no-checkout", CLONE_URL, OUT_DIR]
    )
    shutil.copytree(
        os.path.join(THIS_DIR, 'media'),
        os.path.join(OUT_DIR, 'media'),
    )
    os.environ['REZ_SOURCE_DIR'] = REZ_SOURCE_DIR

    # python utils/process.py  # Replaced by...
    os.chdir(OUT_DIR)
    process_markdown_files()
