#!/usr/bin/env bash

# For verbose run with 1 as argument. (bash us_debt.sh 1)

# Location of database file, change as you see fit, tries to auto create if it doesn't exist.
DB_FILE="$HOME/scripts/db/us_debt.txt"


### DO NOT TOUCH ###
DEPENDENCIES="wget curl jq sed awk tr wc tail head touch cat date grep bc"
CURRENT_DEBT=0
GOLD_PRICE_NOW=0
SILVER_PRICE_NOW=0
REVERSE_REPO_BALANCE=0
M2_MONEY_SUPPLY=0
DATE_TODAY=$(date "+%F")
HEADER="DATE|US_DEBT|GOLD_PRICE_OZ|SILVER_PRICE_OZ|REV_REPO_BALANCE|M2_MONEY_SUPPLY"
[[ $1 -eq 1 ]] && VERBOSE=1 || VERBOSE=0
####################

check_deps() {
	MISSING_DEPS=""
	M_COUNT=0
	for dep in $DEPENDENCIES; do
		if [[ -z $(command -v $dep) ]]; then
			MISSING_DEPS="${MISSING_DEPS}${dep} "
			M_COUNT=$((M_COUNT + 1))
		fi
	done
	if [[ -n $MISSING_DEPS ]]; then
		echo "Error! Dependencies missing:"
		echo "---------------------"
		for mdep in $MISSING_DEPS; do
			echo "$mdep"
		done
		echo "---------------------"
		[[ $M_COUNT -eq 1 ]] && echo "Install the package listed above and try again." || echo "Install the packages listed above and try again."
		Cleanup
		exit 1
	fi
}

check_db_file() {
	if [[ ! -f $DB_FILE ]]; then
		DB_FILE_DIR=$(echo $DB_FILE | sed 's|\(.*\)/.*|\1|')
		_success=0
		if [[ ! -d $DB_FILE_DIR ]]; then
			mkdir -p $DB_FILE_DIR >/dev/null 2>&1
			_success=$?
		fi
		touch $DB_FILE >/dev/null 2>&1
		if [[ $? -ne 0 || $_success -ne 0 ]]; then
			echo "Error! Database file: '$DB_FILE' doesn't exist and can't be created. Check the path and try again."
			Cleanup
			exit 2
		fi
		echo "$HEADER" > $DB_FILE
		echo "Database file created: '$DB_FILE'"
	fi
}

format_number_to_currency() {
	LC_NUMERIC=en_US.UTF-8 printf "%'.2f" $1
}

format_number_repo_balance() {
	TMP_VALUE=$1
	LC_NUMERIC=en_US.UTF-8 printf "%'.f" $((TMP_VALUE * 1000000))
}

format_number_m2_money() {
	TMP_VALUE=$1
	LC_NUMERIC=en_US.UTF-8 printf "%'.f" $((TMP_VALUE * 100000000))
}

get_latest_debt() {
	[[ $(head -n2 $DB_FILE | wc -l) -gt 1 ]] && echo $(tail -n1 $DB_FILE | awk -F "|" '{print $2}' | tr -d ",") || echo "0"
}

remove_duplicates() {
	[[ $(tail -n1 $DB_FILE | grep "$DATE_TODAY") ]] && sed -i "/$DATE_TODAY/d" $DB_FILE 
}

write_to_db_file() {
	printf "%s|%s|%s|%s|%s|%s\n" $DATE_TODAY $CURRENT_DEBT $GOLD_PRICE_NOW $SILVER_PRICE_NOW $REVERSE_REPO_BALANCE $M2_MONEY_SUPPLY >> $DB_FILE
}

verbose_debt() {
	[[ $VERBOSE -eq 1 ]] && echo "$HEADER"
	[[ $VERBOSE -eq 1 ]] && tail -n1 $DB_FILE
}

set_us_debt() {
	wget -q -O /tmp/debt_today.json "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&format=json&page[number]=1&page[size]=1"
	_success=$?
	CURRENT_DEBT=$(cat /tmp/debt_today.json | jq -r ".data[0].tot_pub_debt_out_amt")
	if [[ $_success -ne 0 || $(echo $CURRENT_DEBT | wc -m) -lt 5 ]]; then
		curl -s "https://www.treasurydirect.gov/NP_WS/debt/`date -d "yesterday" '+%Y/%m/%d'`" > /tmp/debt_today.json
		CURRENT_DEBT=$(cat /tmp/debt_today.json | jq -r ".totalDebt")
	fi
	if [[ $(echo $CURRENT_DEBT | tr -cd [0-9] | wc -m) -lt 5 ]]; then
		CURRENT_DEBT=$(get_latest_debt)
	fi
	CURRENT_DEBT=$(format_number_to_currency $CURRENT_DEBT)
}

set_gold_price() {
	curl -s 'https://data-asg.goldprice.org/dbXRates/USD' | jq -r ".items[0].xauPrice" > /tmp/gold_price_now
	if [[ $? -ne 0 || -z $(cat /tmp/gold_price_now | tr -cd [0-9]) || $(cat /tmp/gold_price_now | wc -m) -lt 4 ]]; then
		curl -s 'https://cdn.gold-eagle.com/highcharts/get-prices-exchanged-json.php?symbol=XAUUSDO&currency=USD&unit=oz&resolution=1&numdays=1' | jq -r ".[-1][1]" > /tmp/gold_price_now
	fi
	GOLD_PRICE_NOW=$(cat /tmp/gold_price_now | bc -l | xargs printf %.2f)
	[[ -z $(echo $GOLD_PRICE_NOW | tr -cd [0-9]) || $(echo $GOLD_PRICE_NOW | wc -m) -lt 4 ]] && GOLD_PRICE_NOW=0
	GOLD_PRICE_NOW=$(format_number_to_currency $GOLD_PRICE_NOW)
}

set_silver_price() {
	curl -s 'https://data-asg.goldprice.org/dbXRates/USD' | jq -r ".items[0].xagPrice" > /tmp/silver_price_now
	if [[ $? -ne 0 || -z $(cat /tmp/silver_price_now | tr -cd [0-9]) || $(cat /tmp/silver_price_now | wc -m) -lt 3 ]]; then
		curl -s 'https://cdn.gold-eagle.com/highcharts/get-prices-exchanged-json.php?symbol=XAGUSDO&currency=USD&unit=oz&resolution=1&numdays=1' | jq -r ".[-1][1]" > /tmp/silver_price_now
	fi
	SILVER_PRICE_NOW=$(cat /tmp/silver_price_now | bc -l | xargs printf %.2f)
	[[ -z $(echo $SILVER_PRICE_NOW | tr -cd [0-9]) || $(echo $SILVER_PRICE_NOW | wc -m) -lt 4 ]] && SILVER_PRICE_NOW=0
	SILVER_PRICE_NOW=$(format_number_to_currency $SILVER_PRICE_NOW)
}

set_reverse_repo_balance() {
	curl -s 'https://fred.stlouisfed.org/series/RRPONTSYD' > /tmp/reverse_repo_balance
	_success=$?
	REVERSE_REPO_BALANCE=$(cat /tmp/reverse_repo_balance | grep "td align=\"right\" class=\"series-obs value\"" | head -n1 | sed -e 's/<[^>]*>//g' | tr -cd "[0-9\n]")
	if [[ $_success -ne 0 || -z $(echo $REVERSE_REPO_BALANCE | tr -cd [0-9]) || $(echo $REVERSE_REPO_BALANCE | wc -m) -lt 5 ]]; then
		curl -s 'https://ycharts.com/charts/fund_data.json?calcs=&chartId=&chartType=interactive&correlations=&customGrowthAmount=&dataInLegend=value&dateSelection=range&displayDateRange=false&endDate=&format=real&legendOnChart=false&lineAnnotations=&nameInLegend=name_and_ticker&note=&partner=basic_2000&quoteLegend=false&recessions=false&scaleType=linear&securities=id%3AI%3AUSFAOO1K%2Cinclude%3Atrue%2C%2C&securityGroup=&securitylistName=&securitylistSecurityId=&source=false&splitType=single&startDate=&title=&units=false&useCustomColors=false&useEstimates=false&zoom=1&redesign=true&chartAnnotations=&axisExtremes=&maxPoints=891&chartCreator=false' -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36' | jq -r ".chart_data[0][0].raw_data[-1][1]" > /tmp/reverse_repo_balance
		_success=$?
	fi
	[[ $_success -ne 0 || $(echo $REVERSE_REPO_BALANCE | wc -m) -lt 5 ]] && REVERSE_REPO_BALANCE=0
	REVERSE_REPO_BALANCE=$(format_number_repo_balance $REVERSE_REPO_BALANCE)
}

set_m2_money_supply() {
	curl -s 'https://fred.stlouisfed.org/series/M2SL' > /tmp/m2_money
	_success=$?
	M2_MONEY_SUPPLY=$(cat /tmp/m2_money | grep "td align=\"right\" class=\"series-obs value\"" | head -n1 | sed -e 's/<[^>]*>//g' | tr -cd "[0-9\n]")
	if [[ $_success -ne 0 || -z $(echo $M2_MONEY_SUPPLY | tr -cd [0-9]) || $(echo $M2_MONEY_SUPPLY | wc -m) -lt 5 ]]; then
		curl -s 'https://ycharts.com/charts/fund_data.json?calcs=&chartId=&chartType=interactive&correlations=&customGrowthAmount=&dataInLegend=value&dateSelection=range&displayDateRange=false&endDate=&format=real&legendOnChart=false&lineAnnotations=&nameInLegend=name_and_ticker&note=&partner=basic_2000&quoteLegend=false&recessions=false&scaleType=linear&securities=id%3AI%3AUSM2MSSM%2Cinclude%3Atrue%2C%2C&securityGroup=&securitylistName=&securitylistSecurityId=&source=false&splitType=single&startDate=&title=&units=false&useCustomColors=false&useEstimates=false&zoom=1&redesign=true&chartAnnotations=&axisExtremes=&maxPoints=891&chartCreator=false' -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36' | jq -r ".chart_data[0][0].raw_data[-1][1]" > /tmp/m2_money
		_success=$?
		M2_MONEY_SUPPLY=$(cat /tmp/m2_money)
		[[ $(echo $M2_MONEY_SUPPLY | wc -m) -ge 9 ]] && M2_MONEY_SUPPLY=$((M2_MONEY_SUPPLY / 100))
	fi
	[[ $_success -ne 0 || $(echo $M2_MONEY_SUPPLY | tr -cd [0-9] | wc -m) -lt 4 ]] && M2_MONEY_SUPPLY=0
	M2_MONEY_SUPPLY=$(format_number_m2_money $M2_MONEY_SUPPLY)
}

Cleanup() {
	[[ -f /tmp/debt_today.json ]] && rm -f /tmp/debt_today.json >/dev/null 2>&1
	[[ -f /tmp/gold_price_now ]] && rm -f /tmp/gold_price_now >/dev/null 2>&1
	[[ -f /tmp/silver_price_now ]] && rm -f /tmp/silver_price_now >/dev/null 2>&1
	[[ -f /tmp/reverse_repo_balance ]] && rm -f /tmp/reverse_repo_balance >/dev/null 2>&1
	[[ -f /tmp/m2_money ]] && rm -f /tmp/m2_money >/dev/null 2>&1
}

check_deps
check_db_file
set_us_debt
set_gold_price
set_silver_price
set_reverse_repo_balance
set_m2_money_supply
remove_duplicates
write_to_db_file
verbose_debt
Cleanup
exit 0
