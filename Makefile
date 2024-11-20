SRC=src/

.DEFAULT_GOAL := build

install-uv:
	curl -LsSf https://astral.sh/uv/install.sh | sh

install:
	uv sync --extra dev

refresh-data:
	cd ${SRC} && uv run --env-file ../.env refresh_data.py ../output/data && cd -

build-website:
	cd ${SRC} && uv run --env-file ../.env build_website.py ../output/data ../docs && cd -

test:
	uv run pytest

build: refresh-data build-website