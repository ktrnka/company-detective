SRC=src/

install:
	pipenv install --dev

refresh-data:
	cd ${SRC} && pipenv run python refresh_data.py ../output/data && cd -

build-website:
	cd ${SRC} && pipenv run python build_website.py ../output/data ../docs && cd -

build: refresh-data build-website