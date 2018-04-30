install.packages("tidyverse")
library(zoo); library(xts); library(dplyr); library(PerformanceAnalytics); library(quantmod); library(tidyquant)


head(daily.return)
View(daily.return$Net.Portfolio.Value..USD.)
View(coindesk.bpi)

#--- Portfolio return calculation
portfolio_return <- Return.calculate(xts(daily.return$Net.Portfolio.Value..USD., order.by=as.POSIXct(coindesk.bpi$Date)))
sigma_p <- sd(portfolio_return, na.rm = TRUE)
View(daily.return)
max(portfolio_return, na.rm = TRUE)
View(portfolio_return)

#--- Market return
n <- length(coindesk.bpi$Close.Price)
coindesk.bpi$relative.change <- (coindesk.bpi$Close.Price/lag(coindesk.bpi$Close.Price, 1) - 1)
bpi_return <- Return.calculate(xts(coindesk.bpi$Close.Price, order.by=as.POSIXct(coindesk.bpi$Date)))
sigma_m <- sd(bpi_return, na.rm=TRUE)
View(bpi_return)

#--- Evaluate performance
reg <- lm(portfolio_return ~ bpi_return)
cor(portfolio_return, bpi_return, use = "complete.obs")*sigma_p/sigma_m # method 1
beta <- summary(reg)$coefficients[2,1] # method 2

sqrt(sigma_p^2 - beta^2*sigma_m^2) # method 1
sd(portfolio_return - beta*bpi_return, na.rm = TRUE) # method 2

#--- Annualized performance
annualized_r_p <- Return.annualized(portfolio_return)
annualized_r_m <- Return.annualized(bpi_return)
annualized_s_p <- StdDev.annualized(portfolio_return)
annualized_s_m <- StdDev.annualized(bpi_return)
sqrt(annualized_s_p^2 - beta^2*annualized_s_m^2)
