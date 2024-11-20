SRC=src/

.DEFAULT_GOAL := build

install-uv:
	curl -LsSf https://astral.sh/uv/install.sh | sh

install:
	uv sync --all-extras

refresh-data:
	uv run --directory src/ --env-file ../.env refresh_data.py ../output/data

build-website:
	uv run --directory src/ --env-file ../.env build_website.py ../output/data ../docs

test:
	uv run pytest

vulture:
	uv run vulture --ignore-names 'test_*' src/

build: refresh-data build-website