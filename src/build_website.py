import argparse
import glob
import json
from typing import Dict
import jinja2
from loguru import logger

from unified import UnifiedResult


def main():
    parser = argparse.ArgumentParser(description="Build the website")
    parser.add_argument(
        "input_folder", type=str, help="The folder containing the JSON data files"
    )
    parser.add_argument(
        "output_folder", type=str, help="The folder to output the website to"
    )
    args = parser.parse_args()

    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
    )

    results: Dict[str, UnifiedResult] = {}

    json_files = glob.glob(f"{args.input_folder}/*.json")
    for file_path in json_files:
        with open(file_path, "r") as file:
            data = json.load(file)
            results[file_path] = UnifiedResult(**data)

    for json_path, result in results.items():
        result.to_html_file(
            f"{args.output_folder}/companies/{result.target.as_path_v2()}.html"
        )

    names_to_relative_urls = {
        result.target.company: f"companies/{result.target.as_path_v2()}.html"
        for result in results.values()
    }

    with open(f"{args.output_folder}/index.html", "w") as file:
        file.write(
            templates.get_template("index.html").render(
                names_to_relative_urls=names_to_relative_urls,
                title="Company Detective beta",
            )
        )
        logger.info(f"Generated {file.name}")


if __name__ == "__main__":
    main()
