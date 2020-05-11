SHELL := /bin/bash
.PHONY: all heroku pipenv config groupme

all: heroku pipenv config groupme database

heroku:
	@printf "\n--------------HEROKU--------------\n"
	@echo "Checking if Heroku CLI tools are installed..."
	@brew tap heroku/brew
	@if brew ls --versions heroku; then brew upgrade heroku; else brew install heroku; fi
	@read -p "Heroku app name: " app &&\
		heroku apps:create $$app &&\
		echo "CALLBACK_URL=https://$$app.herokuapp.com" >> .env &&\
		heroku addons:create heroku-postgresql:hobby-dev --app $$app &&\
		heroku git:remote -a $$app &&\
		heroku config:set CALLBACK_URL=https://$$app.herokuapp.com &&\
		git push heroku master
	@printf "\n----------------------------------\n"

pipenv:
	@printf "\n--------------PIPENV--------------\n"
	@echo "Installing pipenv..."
	@if brew ls --versions pipenv; then brew upgrade pipenv; else brew install pipenv; fi
	@printf "\n-----------------------------------\n"

config:
	@printf "\n--------------CONFIG---------------\n"
	@echo "Before continuing, make sure you have created a developer account"
	@echo "at dev.groupme.com. Have your access token on hand, as well as"
	@echo "the callback url found on your Heroku app."
	@read -p "GroupME API token: " token && echo "GROUPME_ACCESS_TOKEN=$$token" >> .env &&\
		heroku config:set "GROUPME_ACCESS_TOKEN=$$token"
	@HEROKU_TOKEN=$$(heroku auth:token | tail -1); heroku config:set "HRKU_TOKEN=$$HEROKU_TOKEN"
	@printf "\n-----------------------------------\n"

groupme:
	@pipenv install -r requirements.txt
	@pipenv run python scripts/create_bot.py

database:
	@printf "\n-----------------------------------"
	@echo "Run the following two lines, then quit with `quit()`."
	@echo " (1) from app import app, db"
	@echo " (2) with app.app_context(): db.create_all()"
	@heroku run python

clean:
	@rm .env
