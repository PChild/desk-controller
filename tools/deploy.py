import argparse
import filecmp
import shutil
from pathlib import Path


# Change this if your CIRCUITPY drive letter changes
DEVICE = Path("E:/")

SRC = Path(__file__).parent.parent / "src"


EXCLUDE = {
    ".git",
    ".gitignore",
    "__pycache__",
    ".DS_Store",
    "settings.toml.example",
}


PROTECTED_DEVICE_FILES = {
    "boot_out.txt",
    "CURRENT.UF2",
}



def should_skip(path):

    for part in path.parts:

        if part in EXCLUDE:
            return True

    return False



def same_file(src, dst):

    try:

        return filecmp.cmp(
            src,
            dst,
            shallow=False
        )

    except OSError:

        return False



def deploy_file(src, dst, dry_run):

    relative = dst.relative_to(
        DEVICE
    )


    if dst.exists() and same_file(src, dst):

        return None


    if dry_run:

        return "UPDATE " + str(relative)


    dst.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        src,
        dst
    )

    return "UPDATED " + str(relative)



def find_deleted_files():

    deleted = []


    for device_file in DEVICE.rglob("*"):

        if device_file.is_dir():
            continue


        relative = device_file.relative_to(
            DEVICE
        )


        if relative.name in PROTECTED_DEVICE_FILES:
            continue


        if should_skip(relative):
            continue


        source_file = SRC / relative


        if not source_file.exists():

            deleted.append(
                device_file
            )


    return deleted



def remove_files(files, dry_run):

    results = []


    for file in files:

        relative = file.relative_to(
            DEVICE
        )


        if dry_run:

            results.append(
                "DELETE " + str(relative)
            )

        else:

            file.unlink()

            results.append(
                "DELETED " + str(relative)
            )


    return results



def main():

    parser = argparse.ArgumentParser(
        description="Deploy CircuitPython files"
    )


    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show changes without copying/deleting"
    )


    parser.add_argument(
        "--yes",
        action="store_true",
        help="do not ask before deleting"
    )


    args = parser.parse_args()


    print()
    print("Source:")
    print(" ", SRC)

    print("Device:")
    print(" ", DEVICE)

    if args.dry_run:

        print()
        print("*** DRY RUN ***")


    changes = []


    # Copy/update
    for src_file in SRC.rglob("*"):

        if src_file.is_dir():

            continue


        relative = src_file.relative_to(
            SRC
        )


        if should_skip(relative):

            continue


        result = deploy_file(
            src_file,
            DEVICE / relative,
            args.dry_run
        )


        if result:

            changes.append(
                result
            )


    # Delete removed files
    deleted = find_deleted_files()


    if deleted and not args.dry_run and not args.yes:

        print()
        print("The following files will be deleted:")

        for f in deleted:

            print(
                " -",
                f.relative_to(DEVICE)
            )


        answer = input(
            "\nContinue? [y/N] "
        )


        if answer.lower() != "y":

            print(
                "Cancelled"
            )

            return


    changes.extend(
        remove_files(
            deleted,
            args.dry_run
        )
    )


    print()

    if changes:

        print("Changes:")

        for change in changes:

            print(
                " ",
                change
            )

    else:

        print(
            "No changes"
        )


    if args.dry_run:

        print()
        print(
            "Dry run complete. No files changed."
        )

    else:

        print()
        print(
            "Deploy complete."
        )



if __name__ == "__main__":

    main()