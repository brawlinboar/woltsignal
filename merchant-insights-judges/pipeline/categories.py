"""Mapping of Merchant Category Codes (MCC, ISO 18245) to 14 category groups.

The grouping is our own proposal (the dataset only ships raw MCC codes and names).
Codes not listed fall into 'Other Services'. The order of WHEN clauses matters.
"""

CATEGORY_GROUPS = [
    "Groceries & Food Stores",
    "Restaurants & Bars",
    "Travel",
    "Local Transport",
    "Fuel & Automotive",
    "Fashion & Beauty",
    "Health & Pharmacy",
    "Cash & Financial",
    "Marketplaces, Discount & Department Stores",
    "Electronics & Digital",
    "Home, Garden & Pets",
    "Entertainment, Sports & Hobbies",
    "Bills, Government & Education",
    "Other Services",
]

CATEGORY_GROUP_SQL = """
CASE
  WHEN {mcc} IN (5411,5422,5441,5451,5462,5499,5921,5993)                          THEN 'Groceries & Food Stores'
  WHEN {mcc} IN (5811,5812,5813,5814)                                              THEN 'Restaurants & Bars'
  WHEN {mcc} BETWEEN 3000 AND 3999
    OR {mcc} IN (4411,4457,4468,4511,4582,4722,4723,5962,7011,7012,7032,7033,
                 7512,7513,7519)                                                   THEN 'Travel'
  WHEN {mcc} IN (4011,4111,4112,4119,4121,4131,4784,4789,7523)                     THEN 'Local Transport'
  WHEN {mcc} IN (5013,5172,5511,5521,5532,5533,5541,5542,5551,5552,5561,5571,5592,
                 5598,5599,5983,7531,7534,7535,7538,7542,7549)                     THEN 'Fuel & Automotive'
  WHEN {mcc} BETWEEN 5611 AND 5699
    OR {mcc} IN (5094,5137,5139,5944,5948,5949,5977,7230,7297,7298)                THEN 'Fashion & Beauty'
  WHEN {mcc} BETWEEN 8011 AND 8099 OR {mcc} IN (5047,5122,5912,5975,5976)          THEN 'Health & Pharmacy'
  WHEN {mcc} IN (4829,6010,6011,6012,6051,6211,6540)                               THEN 'Cash & Financial'
  WHEN {mcc} BETWEEN 5960 AND 5969
    OR {mcc} IN (5262,5300,5309,5310,5311,5331,5399)                               THEN 'Marketplaces, Discount & Department Stores'
  WHEN {mcc} IN (4812,4814,4816,5044,5045,5732,5733,5734,5735,5815,5816,5817,5818,
                 7372,7375,7379)                                                   THEN 'Electronics & Digital'
  WHEN {mcc} BETWEEN 1500 AND 2999 OR {mcc} BETWEEN 5200 AND 5271
    OR {mcc} BETWEEN 5712 AND 5722
    OR {mcc} IN (742,763,780,5021,5039,5046,5051,5065,5072,5074,5085,5193,5198,
                 5992,5995)                                                        THEN 'Home, Garden & Pets'
  WHEN {mcc} BETWEEN 7800 AND 7999
    OR {mcc} IN (5192,5940,5941,5942,5943,5945,5946,5947,5994)                     THEN 'Entertainment, Sports & Hobbies'
  WHEN {mcc} BETWEEN 8200 AND 8399 OR {mcc} BETWEEN 9000 AND 9998
    OR {mcc} IN (4899,4900,6300,6513)                                              THEN 'Bills, Government & Education'
  ELSE 'Other Services'
END
"""


def category_group_sql(mcc_column: str) -> str:
    return CATEGORY_GROUP_SQL.format(mcc=mcc_column)
