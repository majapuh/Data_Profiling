# Data_Profiling

Algorithm originated from DWH migration project. 
Table structures and all data included were migrated from one database to another. 
Issues arised from particular data types not being supported in the new database. 

Specific data types would have to be replaced by semi-equivalent types existing in the new DBMS. 
In order to do that, data had to be profiled and manually analized, as there was not, at the time of the project, any tool that automates the procedure.

Legacy DMBS was IMB Netezza, new DMBS was Vertica. The main isuess was conversion of NVARCHAR columns to VARCHAR. 

Vertica doesn't support the National Character Varying data type, so it is necessary to convert all of the attributes that have National Character Varying data type on Netezza to a Character Varying. 
The functionality of Nvarchar(Netezza) to support all utf-8 characters was retained in Varchar (Vertica).  

However, Vertica uses byte oriented text column length, opposite to Netezza’s character oriented semantic. Due to this byte oriented principle, some characters specific to non-English alphabet (for instance ć, đ, ž, dž) take up more memory when being stored – one character requires more than one byte. Because of that it is necessary to enlarge the length of the columns that were originaly Nvarchar on Netteza, i.e. from Nvarchar(10) to Varchar(20). 
On the other side, this kind of increase of column's precision has to be done carefully, with some kind of data profiling (manual or automated) involved. The reason for that precaution lies in Vertica's memory allocation strategy during multiple joins in a query.  When tables that contain vast amounts of data are joined, memory acquired is, sometimes, based on the defined size of lookup columns. If lookup columns are of type varchar, memory acquired for executing a single query often is not even enough for successful execution. 


Algorithm was made to automate this process. It connects to do legacy DMBS, profiles the data, and determines the right size for the converted varchar column. 

