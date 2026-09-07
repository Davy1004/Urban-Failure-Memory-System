"""MySQL UNSIGNED integer aliases that still work on other dialects."""
from sqlalchemy import BigInteger, Integer, SmallInteger
from sqlalchemy.dialects import mysql

UInt = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
UBigInt = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
USmallInt = SmallInteger().with_variant(mysql.SMALLINT(unsigned=True), "mysql")
UTinyInt = SmallInteger().with_variant(mysql.TINYINT(unsigned=True), "mysql")
