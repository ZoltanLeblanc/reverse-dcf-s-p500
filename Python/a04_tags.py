"""Listes de tags XBRL us-gaap utilises pour extraire les fondamentaux.
Entree : aucune. Sortie : constantes importees par a05_fundamental_extraction.py.
Chaque liste TAGS_* est classee par ordre de priorite ; les commentaires en fin de ligne
citent des societes qui utilisent le tag. MIN/MAX_DURATION_DAYS bornent la duree (en jours)
d'une valeur annuelle.

Contenu : revenue, EBIT, D&A, impot, interets, cash flow operationnel, capex, tresorerie,
placements, dette long terme et court terme, nombre d'actions, resultat avant impot.
"""
MIN_DURATION_DAYS = 350
MAX_DURATION_DAYS = 380

TAGS_REVENUE = [
    'Revenues',
    'RevenueFromContractWithCustomerExcludingAssessedTax',
    'RevenueFromContractWithCustomerIncludingAssessedTax',
    'SalesRevenueNet',
    'SalesRevenueGoodsNet',
    'SalesRevenueServicesNet',
    'RegulatedAndUnregulatedOperatingRevenue',
    'OilAndGasRevenue',
    'RefiningAndMarketingRevenue', 
    'HealthCareOrganizationRevenue', 
    'RevenuesNetOfInterestExpense', 
    'RealEstateRevenueNet', 
    'OperatingLeasesIncomeStatementLeaseRevenue',
    'NaturalGasProductionRevenue', 
    'OilAndCondensateRevenue',
    'FoodAndBeverageRevenue', # Chipotle
    'ContractsRevenue', # Applied Energetics
    'RevenueMineralSales', # Newmont, Freeport
]

TAGS_EBIT = [
    'OperatingIncomeLoss',
]

TAGS_DEPRECIATION_AMORTIZATION = [
    'DepreciationDepletionAndAmortization',
    'DepreciationAndAmortization',
    'DepreciationAmortizationAndAccretionNet',
    'Depreciation',
]

TAGS_DA_SECOURS = [ # D&A d'un poste (cout des ventes, forage...) : dernier recours quand aucun total n'est publie
    'ResultsOfOperationsDepreciationDepletionAndAmortizationAndValuationProvisions',
    'CostOfServicesDepreciationAndAmortization',
    'CostOfGoodsAndServicesSoldDepreciationAndAmortization',
    'CostOfGoodsSoldDepreciationAndAmortization',
    'CostOfGoodsSoldDepreciationDepletionAndAmortization',
    'CostOfServicesDepreciation',
    'CostOfGoodsAndServicesSoldDepreciation',
    'DepreciationNonproduction',
]

TAGS_INCOME_TAX = [
    'IncomeTaxExpenseBenefit',
    'IncomeTaxExpenseBenefitContinuingOperations',
]

TAGS_INTEREST_EXPENSE = [
    'InterestExpense',
    'InterestExpenseDebt',
    'InterestAndDebtExpense',
    'InterestExpenseNonoperating',
    'InterestExpenseLongTermDebt',
    'InterestExpenseDebtExcludingAmortization',
    'InterestPaid',
    'InterestPaidNet',
]

TAGS_OCF = [
    'NetCashProvidedByUsedInOperatingActivities',
    'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations',
]


TAGS_CAPEX = [
    'PaymentsToAcquirePropertyPlantAndEquipment',
    'PaymentsToAcquireProductiveAssets',
    'PaymentsToAcquireOilAndGasPropertyAndEquipment',
    'PaymentsToAcquireOtherPropertyPlantAndEquipment', # Eli Lilly, ADP
    'PaymentsToAcquireOtherProductiveAssets', # Verizon, Roper
    'PaymentsForCapitalImprovements', # Corning, Snap-on, Gartner
    'PaymentsForProceedsFromProductiveAssets', # Waters, Corning avant 2018, KB Home, Simon
    'PaymentsToExploreAndDevelopOilAndGasProperties', # Apache, Cimarex, Coterra, Newfield
]

# Dernier recours : ce tag melange souvent capex et acquisitions de gisements (FANG, CXO) ; utilise seulement pour une annee sans autre tag
TAGS_CAPEX_DERNIER_RECOURS = ['PaymentsToAcquireOilAndGasProperty']

TAGS_CASH = [
    'CashAndCashEquivalentsAtCarryingValue',
    'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',
    'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations', 
    'CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations', 
    'Cash', 
    'CashAndDueFromBanks', 
    'CashCashEquivalentsAndShortTermInvestments',
]

TAGS_LONG_TERM_DEBT = [
    'LongTermDebtAndCapitalLeaseObligations',
    'LongTermDebtNoncurrent',
    'LongTermDebt',
    'DebtAndCapitalLeaseObligations', # Aflac, Ford
    'UnsecuredLongTermDebt', # Cadence
    'SeniorLongTermNotes', # Arch Capital
    'SeniorNotes', # Verisign, Extra Space, Raymond James
    'NotesPayable', # Aflac, Extra Space
    'ConvertibleDebt',
    'UnsecuredDebt',
    'SecuredDebt',
    'JuniorSubordinatedNotes', # Berkley
    'ConvertibleLongTermNotesPayable', # Akamai, Datadog, ServiceNow, Dexcom
    'ConvertibleDebtNoncurrent', # Palo Alto, Lumentum, Teradyne
    'OtherLongTermDebtNoncurrent', # ADP
    'SecuredLongTermDebt',
    'NonRecourseDebt', # AES
    'LongTermLineOfCredit', 
    'LineOfCredit', 
    'NotesAndLoansPayable', 
    'FinanceLeaseLiabilityNoncurrent', 
    'CapitalLeaseObligationsNoncurrent',
    'LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities', # General Motors
    'LongTermNotesPayable',
    'LoansPayable',
    'LongTermLoansFromBank',
]

TAGS_CURRENT_DEBT = [
    'LongTermDebtCurrent',
    'DebtCurrent',
    'LongTermDebtAndCapitalLeaseObligationsCurrent',
    'ShortTermBorrowings',
    'ConvertibleNotesPayableCurrent',
    'ConvertibleDebtCurrent',
    'SecuredDebtCurrent',
    'ShortTermBankLoansAndNotesPayable', # Expeditors
    'NotesPayableCurrent',
    'LinesOfCreditCurrent', 
    'FinanceLeaseLiabilityCurrent', 
    'CapitalLeaseObligationsCurrent',
    'LoansPayableToBankCurrent',
]

TAGS_SHARES_OUTSTANDING = [
    'CommonStockSharesOutstanding',
    'WeightedAverageNumberOfSharesOutstandingBasic',
    'WeightedAverageNumberOfDilutedSharesOutstanding', # Tyson et les societes a plusieurs classes d'actions
    'WeightedAverageNumberOfShareOutstandingBasicAndDiluted', # Certaines societes ne publient que ce tag combine
]   

TAGS_PRETAX_INCOME = [
    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
]



# Placements a court terme, ajoutes a la tresorerie
TAGS_ST_INVEST = [
    'ShortTermInvestments',
    'MarketableSecuritiesCurrent',
    'AvailableForSaleSecuritiesDebtSecuritiesCurrent',
    'AvailableForSaleSecuritiesCurrent',
]


# Titres non courants (obligations, placements a long terme), ajoutes a la tresorerie. JAMAIS LongTermInvestments (inclut des participations)
TAGS_LT_SECURITIES = [
    'MarketableSecuritiesNoncurrent',
    'AvailableForSaleSecuritiesNoncurrent', # Apple 2015
    'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent',
]


# Tags du vrai capex des pétrolières : si l'un d'eux existe pour l'année, le tag d'acquisitions de gisements n'est jamais utilisé
TAGS_CAPEX_PETROLE = ['PaymentsToExploreAndDevelopOilAndGasProperties', 'PaymentsToAcquireOilAndGasPropertyAndEquipment']
