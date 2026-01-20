#!/usr/bin/env python3
"""Example skill script demonstrating the expected format."""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Example skill script")
    parser.add_argument("--option", help="An example option", default="default")
    args = parser.parse_args()

    print(f"Running example skill with option: {args.option}")


if __name__ == "__main__":
    main()
