import argparse


def real_main(args):
    print(f"args: {args}")


def main():
    parser = argparse.ArgumentParser(description="ps3mfw")
    parser.add_argument(
        "--in-pup", type=str, help="Input PUP FW file", metavar="IN_PUP"
    )
    parser.add_argument(
        "--out-pup", type=str, help="Output PUP FW file", metavar="OUT_PUP"
    )
    parser.add_argument(
        "--out-dir", type=str, help="Output directory", metavar="OUT_DIR"
    )
    real_main(parser.parse_args())
    return 0
