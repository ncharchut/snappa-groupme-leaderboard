SHELL := /bin/bash
.PHONY: all heroku pipenv config groupme

all: heroku pipenv config groupme

heroku:
	@echo "Checking if Heroku CLI tools are installed..."
	@brew tap heroku/brew
	@if brew ls --versions heroku; then brew upgrade heroku; else brew install heroku; fi
	@read -p "Heroku app name: " app &&\
		heroku apps:create $$app &&\
		echo "CALLBACK_URL=https://$$app.herokuapp.com" >> .env &&\
		heroku addons:create heroku-postgresql:hobby-dev --app $$app &&\
		heroku git:remote -a $$app &&\
		heroku config:set CALLBACK_URL=https://$$app.herokuapp.com

pipenv:
	@echo "Installing pipenv..."
	@if brew ls --versions pipenv; then brew upgrade pipenv; else brew install pipenv; fi

config:
	@echo "Before continuing, make sure you have created a developer account"
	@echo "at dev.groupme.com. Have your access token on hand, as well as"
	@echo "the callback url found on your Heroku app."
	@read -p "GroupME API token: " token && echo "ACCESS_TOKEN=$$token" >> .env &&\
		heroku config:set "ACCESS_TOKEN=$$token"

groupme:
	@pipenv install -r requirements.txt
	@pipenv run python scripts/create_bot.py

clean:
	@rm .env
