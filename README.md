# StckHm
(demo link will be placed here later)
I'm still writing the README file :(\
StckHm is a portfolio tracking web application that I built during the summer of 2021 after realising the lack of support for tracking portfolios across multiple brokerages. Many have used spreadsheets which are not as visually appealing and at the same time more troublesome to update compared to what brokerages offer.\
StckHm uses a combination of graphs and charts to help you visualise your portfolio growth throughout your investing journey and the best part is, you do not have to update the prices of your holdings manually! :D Prices of US stocks are updated using Finnhub's API while closing prices of Singapore Stocks and all ETFs are updated using investpy (since SGX's API is only available for clearing partners >:( )\
With that said, I have decided to not live host this webapp because I feel that I do not have any rights to see what your holdings are since some may consider it as 'private'. Instead, I will be providing a guide on how to run this webapp on your pc (hopefully it's not hard HAHA)\

## Before Doing anything
### Install requirements
Do `pip install requirements.txt` in your python terminal/console
### Getting the API keys
You will need two API keys, one from https://finnhub.io/, and another from https://app.exchangerate-api.com/ \
## Setting Up
Replace `user_id = "demo"` with `user_id = "ANY_USERNAME_YOU_WANT"` where `ANY_USERNAME_YOU_WANT` is well, any username you want the application to identify you by\
Replace `er_token = os.getenv("exchange_rate_token")` with `er_token = YOUR_TOKEN_FROM_EXCHANGERATE_API` where `YOUR_TOKEN_FROM_EXCHANGERATE_API` is your token from exchangerate-api\
Replace `token = os.getenv("finnhub_api_key")` with `token = YOUR_API_TOKEN_FROM_FINNHUB` where `YOUR_API_TOKEN_FROM_FINNHUB` is your token from Finnhub\
You can test to see if the application works by right-clicking anywhere in the text editor and selecting "run app.py" or typing `flask run` (I think) in your python console/terminal\
## Coming to an end
First add your capital (ie the amount you have put into your portfolio in cash) using the "Deposit/Withdraw" card under "Edit Positions", then proceed to add your holdings using "Add/Sell/Edit Positions" card on the same page. PLEASE ADD YOU HOLDINGS ACCURATELY SO THAT YOU WILL DO MINIMAL EDITS AND CALCULATIONS WILL BE ACCURATE 😭.\
Afterwards you can click around to familiarise yourself with the webapp and I hope you will enjoy using it as much as I do.

## A little bit about myself
Thanks for reading all the way till the end 😬. I'm Darryl, currently a Computer Science undergraduate at Singapore's Nanyang Technological University going into Year 2 (as of August 2021) and I really enjoy challenging myself through projects like this as well as programming questions on LeetCode. I had a lot of fun (and pain) building StckHm after I came up with the idea with 1 month of summer left :D I feel that it's important to have hands on practices to complement theoretical studies from college which does not teach much about how to build projects like this (at least not yet for my case). Throughout the past month I have grown fond of development although there are still many areas to improve on which brings me to why this webapp is named 'StckHm'. StckHm is a wordplay on 'Stockholm Syndrome', which is a play on the word 'Stock' 😀 Maybe I'll do one more webapp to complement StckHm and give it the name 'Syndrm'. Who knows...
