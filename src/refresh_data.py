import argparse
import asyncio
from datetime import datetime, timedelta
import os
from typing import Optional
from zoneinfo import ZoneInfo
from loguru import logger
from pydantic import ValidationError

import unified
from core import Seed, SeedValidator, init
import stored_config

TIME_ZONE = ZoneInfo("America/Los_Angeles")

def get_file_modified_time(file_path: str) -> Optional[datetime]:
    if os.path.exists(file_path):
        return datetime.fromtimestamp(os.path.getmtime(file_path), tz=TIME_ZONE)
    else:
        return None


def should_rebuild(
    target: Seed,
    file_path: str,
    max_age: timedelta = timedelta(days=7),
    force_refresh_substring: Optional[str] = None,
    config_last_modified: Optional[datetime] = None,
) -> bool:
    if (
        force_refresh_substring
        and force_refresh_substring.lower() in target.company.lower()
    ):
        return True

    last_modified = get_file_modified_time(file_path)
    if last_modified is None:
        return True
    
    # If the config was modified more recently than the file, so the file is stale
    if config_last_modified and config_last_modified > last_modified:
        return True

    return (last_modified - datetime.now(TIME_ZONE)) > max_age


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

    for orm_company in stored_config.Company.all_approved():
        target = orm_company.to_core_company()
        output_json = f"{args.output_folder}/{target.as_path_v2()}.json"

        refresh_days = orm_company.refresh_days or 30

        if should_rebuild(
            target,
            output_json,
            max_age=timedelta(days=refresh_days),
            force_refresh_substring=args.force_refresh,
            config_last_modified=orm_company.last_modified,
        ):
            logger.info(f"Building {output_json}...")

            try:
                SeedValidator.validate(target)
            except ValidationError as e:
                logger.error(f"Validation error for {target}: {e}")
                raise e

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
