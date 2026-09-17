import os
import sys
import re
import tempfile
import shutil
import getopt
import subprocess

from pypdf import PdfReader, PdfWriter


def a2b(x):
    """Convert ASCII string to bytes."""
    return x.encode("ascii")


def iscolorppm(filename):
    """Return True if the PPM file contains any non-grayscale pixels."""
    with open(filename, "rb") as f:
        data = f.read()

    # PPM headers may contain whitespace and comments.
    comments_re = re.compile(a2b(r"^([^ \t\n]*)#[^\n]*\n"))
    split_re = re.compile(a2b(r"^([ \t\n]|#[^\n]*\n)+([^ \t\n#])"))
    tok_re = re.compile(a2b(r"^([^ \t\n]*)([ \t\n].*)"), re.DOTALL)

    toks = []

    while len(toks) < 4:
        while split_re.match(data):
            data = split_re.sub(rb"\2", data)

        while comments_re.match(data):
            data = comments_re.sub(rb"\1", data)

        match = tok_re.match(data)

        if match is None:
            raise ValueError(f"Invalid PPM header: {filename}")

        tok, data = match.groups()
        toks.append(tok)

    magic = toks[0]
    width, height, max_color = map(int, toks[1:])

    # Skip whitespace byte after header
    data = data[1:]

    if magic == b"P3":
        binary = False

    elif magic == b"P6":
        binary = True

    else:
        raise ValueError(
            f"{filename} is not a valid PPM file"
        )

    data_len = width * height * 3

    if binary:
        if max_color > 255:
            # Each sample uses two bytes.
            data_len *= 2
            data = (
                data[1:data_len:2]
                + data[:data_len:2]
            )

    else:
        data = [
            int(x)
            for x in data.split()
        ]

    if len(data) < data_len:
        raise ValueError(
            f"PPM file appears truncated: {filename}"
        )

    triples = zip(
        data[0:data_len:3],
        data[1:data_len:3],
        data[2:data_len:3],
    )

    black_and_white = all(
        a == b == c
        for a, b, c in triples
    )

    return not black_and_white


def find_ghostscript():
    """
    Automatically find Ghostscript.

    Windows:
        gswin64c
        gswin32c

    Linux/macOS:
        gs
    """

    for command in (
        "gswin64c",
        "gswin32c",
        "gs",
    ):
        path = shutil.which(command)

        if path:
            return path

    raise RuntimeError(
        "Ghostscript was not found.\n"
        "Please make sure gswin64c (Windows) "
        "or gs (Linux/macOS) is in PATH."
    )


def write_pdf(
    reader,
    page_indexes,
    output_name,
    verbose=False,
):
    """
    Write selected pages to a new PDF.

    page_indexes uses zero-based indexes.
    """

    writer = PdfWriter()

    for page_index in page_indexes:
        writer.add_page(
            reader.pages[page_index]
        )

    # Try to preserve original PDF metadata
    try:
        if reader.metadata:
            metadata = {
                str(k): str(v)
                for k, v
                in reader.metadata.items()
                if v is not None
            }

            writer.add_metadata(metadata)

    except Exception:
        pass

    with open(output_name, "wb") as f:
        writer.write(f)

    if verbose:

        page_numbers = ", ".join(
            str(i + 1)
            for i in page_indexes
        )

        print()
        print(f"Created: {output_name}")
        print(f"Pages: {page_numbers}")


def pdfcolorsplit(
    file,
    doublesided,
    merge,
    verbose,
):
    """
    Analyze PDF and split into color
    and black-and-white PDFs.
    """

    if verbose:
        print()
        print("=" * 60)
        print(f"Analyzing: {file}")
        print("=" * 60)

    if not os.path.isfile(file):
        raise FileNotFoundError(
            f"PDF not found: {file}"
        )

    # Find Ghostscript automatically
    gs = find_ghostscript()

    if verbose:
        print(f"Ghostscript: {gs}")
        print()

    tmpdir = tempfile.mkdtemp(
        prefix="pdfcs_"
    )

    try:

        output_pattern = os.path.join(
            tmpdir,
            "tmp%06d.ppm",
        )

        gs_args = [
            gs,
            "-sDEVICE=ppmraw",
            "-dBATCH",
            "-dNOPAUSE",
            "-dSAFER",

            # Low resolution is enough for checking color.
            # This makes analysis much faster.
            "-r20",

            f"-sOutputFile={output_pattern}",
        ]

        if not verbose:
            gs_args.append("-q")

        gs_args.append(file)

        #
        # Important:
        #
        # subprocess is used instead of os.system.
        #
        # This works much better with:
        #   Chinese paths
        #   Spaces in filenames
        #   Windows paths
        #
        subprocess.run(
            gs_args,
            check=True,
        )

        ppms = sorted(
            os.path.join(
                tmpdir,
                name,
            )
            for name in os.listdir(tmpdir)
            if name.lower().endswith(".ppm")
        )

        if not ppms:
            raise RuntimeError(
                "Ghostscript did not generate "
                "any PPM pages."
            )

        iscolor = []

        print()
        print("Page analysis:")
        print("-" * 30)

        for page_no, ppm in enumerate(
            ppms,
            start=1,
        ):

            color = iscolorppm(ppm)

            iscolor.append(color)

            if verbose:
                if color:
                    status = "COLOR"
                else:
                    status = "B/W"

                print(
                    f"Page {page_no:>4}: "
                    f"{status}"
                )

    finally:

        # Always clean temporary image files
        shutil.rmtree(
            tmpdir,
            ignore_errors=True,
        )

    num_pages = len(iscolor)

    #
    # Duplex handling
    #
    # If printing double-sided:
    #
    # Page 1 + Page 2 = one sheet
    # Page 3 + Page 4 = one sheet
    #
    # If either side is color,
    # treat both sides as color.
    #
    if doublesided:

        if verbose:
            print()
            print(
                "Duplex mode enabled."
            )

        for i in range(
            0,
            num_pages - 1,
            2,
        ):

            pair_is_color = (
                iscolor[i]
                or
                iscolor[i + 1]
            )

            iscolor[i] = pair_is_color
            iscolor[i + 1] = pair_is_color

    else:

        if verbose:
            print()
            print(
                "Simplex mode enabled."
            )

    #
    # Read original PDF
    #

    reader = PdfReader(file)

    if len(reader.pages) != num_pages:
        raise RuntimeError(
            "Page count mismatch:\n"
            f"PDF has {len(reader.pages)} pages\n"
            f"Ghostscript rendered {num_pages} pages"
        )

    #
    # Output filename
    #

    if file.lower().endswith(".pdf"):
        base_name = file[:-4]

    else:
        base_name = file

    suffixes = [
        "_bwsplit.pdf",
        "_colorsplit.pdf",
    ]

    #
    # Normal mode
    #
    # Merge every black/white page into one PDF
    # Merge every color page into one PDF
    #

    if merge:

        bw_pages = [
            i
            for i, color
            in enumerate(iscolor)
            if not color
        ]

        color_pages = [
            i
            for i, color
            in enumerate(iscolor)
            if color
        ]

        print()
        print("=" * 60)
        print("Result")
        print("=" * 60)

        print(
            f"Black/White pages: "
            f"{len(bw_pages)}"
        )

        print(
            f"Color pages:       "
            f"{len(color_pages)}"
        )

        #
        # Black & white PDF
        #

        if bw_pages:

            bw_output = (
                base_name
                + suffixes[0]
            )

            write_pdf(
                reader,
                bw_pages,
                bw_output,
                verbose,
            )

            print()
            print(
                f"B/W PDF:\n{bw_output}"
            )

        else:

            print()
            print(
                "No black-and-white pages found."
            )

        #
        # Color PDF
        #

        if color_pages:

            color_output = (
                base_name
                + suffixes[1]
            )

            write_pdf(
                reader,
                color_pages,
                color_output,
                verbose,
            )

            print()
            print(
                f"Color PDF:\n{color_output}"
            )

        else:

            print()
            print(
                "No color pages found."
            )

    #
    # -m mode
    #
    # Write each continuous section
    # into a separate PDF.
    #

    else:

        start = 0
        section_number = 1

        for i in range(
            1,
            num_pages + 1,
        ):

            end_of_section = (
                i == num_pages
                or
                iscolor[i] != iscolor[start]
            )

            if end_of_section:

                color = iscolor[start]

                page_indexes = list(
                    range(
                        start,
                        i,
                    )
                )

                output_name = (
                    f"{base_name}_"
                    f"{section_number:03d}"
                    f"{suffixes[1 if color else 0]}"
                )

                write_pdf(
                    reader,
                    page_indexes,
                    output_name,
                    verbose,
                )

                section_number += 1
                start = i

    print()
    print("Done.")


def usage():

    progname = os.path.basename(
        sys.argv[0]
    )

    print()
    print(
        f"Usage: {progname} "
        "[OPTIONS] <PDF-file(s)>"
    )

    print()

    print(
        "Split PDF files into color "
        "and black-and-white pages."
    )

    print()

    print("Options:")

    print(
        "   -s  Simplex mode "
        "(single-sided printing)"
    )

    print(
        "       Without -s, "
        "duplex mode is used."
    )

    print()

    print(
        "   -m  Write each continuous "
        "section as a separate PDF"
    )

    print()

    print(
        "   -v  Show detailed information"
    )

    print()

    print(
        "   -h  Show this help"
    )

    print()


def main():

    try:

        opt_pairs, filenames = (
            getopt.gnu_getopt(
                sys.argv[1:],
                "hvms",
                [
                    "help",
                ],
            )
        )

    except getopt.GetoptError as err:

        print(err)

        usage()

        sys.exit(1)

    opts = [
        option
        for option, _
        in opt_pairs
    ]

    if (
        "-h" in opts
        or
        "--help" in opts
        or
        not filenames
    ):

        usage()

        sys.exit(0)

    #
    # Options
    #

    verbose = "-v" in opts

    #
    # Without -m:
    #
    # all B/W pages -> one PDF
    # all color pages -> one PDF
    #
    merge = "-m" not in opts

    #
    # Without -s:
    #
    # assume double-sided printing
    #
    # With -s:
    #
    # single-sided printing
    #
    doublesided = "-s" not in opts

    try:

        for file in filenames:

            pdfcolorsplit(
                file=file,
                doublesided=doublesided,
                merge=merge,
                verbose=verbose,
            )

    except Exception as exc:

        print()
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
