import argparse
import asyncio
from datetime import datetime, timedelta
import os
from typing import Optional
from loguru import logger

import unified
from core import Seed, init
import airtable


def get_file_age(file_path: str) -> Optional[timedelta]:
    if os.path.exists(file_path):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        return datetime.now() - file_mod_time
    else:
        return None


def should_rebuild(
    target: Seed,
    file_path: str,
    max_age: timedelta = timedelta(days=7),
    force_refresh_substring: Optional[str] = None,
) -> bool:
    if (
        force_refresh_substring
        and force_refresh_substring.lower() in target.company.lower()
    ):
        return True

    age = get_file_age(file_path)
    if age is None:
        return True
    return age > max_age


async def main():
    parser = argparse.ArgumentParser(description="Refresh the data")
    parser.add_argument(
        "--force-refresh",
        type=str,
        help="Force a refresh for companies containing this string",
    )
    parser.add_argument(
        "output_folder", type=str, help="The folder to output the data to"
    )
    args = parser.parse_args()

    init()

    companies = airtable.load_into_pandas()

    for _, row in companies.sort_values("fields.Name").iterrows():
        target = airtable.row_to_seed(row)
        output_json = f"{args.output_folder}/{target.as_path_v2()}.json"

        # NOTE: Without the dropna, .get returns NaN which then causes the timedelta to fail
        refresh_days = row.dropna().get("fields.Refresh Days", 21)

        if should_rebuild(
            target,
            output_json,
            max_age=timedelta(days=refresh_days),
            force_refresh_substring=args.force_refresh,
        ):
            logger.info(f"Building {output_json}...")

            try:
                unified_result = await unified.run(
                    target,
                    # TODO: Allow some customization of these parameters
                    num_reddit_threads=10,
                    max_glassdoor_review_pages=5,
                    max_glassdoor_job_pages=0,
                    max_news_articles=20,
                )

                with open(output_json, "w") as json_file:
                    json_file.write(unified_result.model_dump_json(indent=2))
            except IndexError as e:
                logger.error(f"Error, skipping {target.company}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
