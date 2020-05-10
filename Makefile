.PHONY: all heroku pipenv groupme

all: heroku pipenv groupme

heroku:
	@echo "Checking if Heroku CLI tools are installed..."
	@brew tap heroku/brew
	@if brew ls --versions heroku; then brew upgrade heroku; else brew install heroku; fi

pipenv:
	@echo "Installing pipenv..."
	@if brew ls --versions pipenv; then brew upgrade pipenv; else brew install pipenv; fi

groupme:
	@echo "Before continuing, make sure you have created a developer account"
	@echo "at dev.groupme.com. Have your access token on hand, as well as"
	@echo "the callback url found on your Heroku app."
	@pipenv install -r requirements.txt
	@pipenv run python scripts/create_bot.py
