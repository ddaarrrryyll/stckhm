# StckHm
https://stckhm.herokuapp.com/home \
(Sometimes investpy will return failed query for some reason which crashes the site but it should be working natively :D)\
StckHm is a portfolio tracking web application that I built during the summer of 2021 after realising the lack of support for tracking portfolios across multiple brokerages. Many have used spreadsheets which are not as visually appealing and at the same time more troublesome to update compared to what brokerages offer.\
StckHm uses a combination of graphs and charts to help you visualise your portfolio growth throughout your investing journey and the best part is, you do not have to update the prices of your holdings manually! :D Prices of US stocks are updated using Finnhub's API while closing prices of Singapore Stocks and all ETFs are updated using investpy (since SGX's API is only available for clearing partners >:( )\
With that said, I have decided to not live host this webapp because I feel that I do not have any rights to see what your holdings are since some may consider it as 'private'. Instead, I will be providing a guide on how to run this webapp on your pc (hopefully it's not hard HAHA)

## Screenshots
### Main/Home page
![image](https://user-images.githubusercontent.com/51407026/133651633-06e0a88d-62a3-4a4e-a0e3-86c9c7691c2f.png)
### Performance page (keeps track of all your current and previous plays)
![image](https://user-images.githubusercontent.com/51407026/133651747-543b537f-da80-41fc-8515-4d958beeb2cb.png)
### Edit Positions page (page that allows you to edit your positions)
![image](https://user-images.githubusercontent.com/51407026/133651836-0f932013-2ed2-4789-8d11-52f81828b3c6.png)


## Before Doing anything
### Download all the files
Download files as zip then extract
### Or you can git clone if you prefer
Do `git clone https://github.com/ddaarrrryyll/stckhm` in your python terminal/console
### Install requirements
Do `pip install requirements.txt` in your python terminal/console
### Getting the API keys
You will need two API keys, one from https://finnhub.io/, and another from https://app.exchangerate-api.com/ 
## Setting Up
Replace `user_id = "demo"` with `user_id = "ANY_USERNAME_YOU_WANT"` where `ANY_USERNAME_YOU_WANT` is well, any username you want the application to identify you by\
Replace `er_token = os.getenv("exchange_rate_token")` with `er_token = YOUR_TOKEN_FROM_EXCHANGERATE_API` where `YOUR_TOKEN_FROM_EXCHANGERATE_API` is your token from exchangerate-api\
Replace `token = os.getenv("finnhub_api_key")` with `token = YOUR_API_TOKEN_FROM_FINNHUB` where `YOUR_API_TOKEN_FROM_FINNHUB` is your token from Finnhub\
You can test to see if the application works by right-clicking anywhere in the text editor and selecting "run app.py" or typing `flask run` (I think) in your python console/terminal
## Setting up internally
First add your capital (ie the amount you have put into your portfolio in cash) using the "Deposit/Withdraw" card under "Edit Positions", then proceed to add your holdings using "Add/Sell/Edit Positions" card on the same page. Please try to add your holdings accurately so minimal edits are required and calculations can be done more accurately.\
Afterwards you can click around to familiarise yourself with the webapp and I hope you will enjoy using it as much as I do.

