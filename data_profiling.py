import pyodbc
import os, sys
import argparse
import string


def connect_to_db (): 
	conn = pyodbc.connect(**conn_info)
	return conn

	
'''
Recalculates column's width.
'''	
def recalculate_column_width(lengths, values, column_width):
	new_column_width=0
	width_changed = False
	double_width = False
	
	diff_ratios = [(len(x.encode('utf-8'))-len(x))/len(x) for x in values]
	
	lengths_special = []
	
	for i in range (len(diff_ratios)): 
		if diff_ratios[i] > 0: 
			lengths_special.append(lengths[i])
	
	values = ''.join(values)
		
	#translator = str.maketrans('', '', string.punctuation)
	#values = values.translate(translator)
	
	if len(values) != len(values.encode('utf-8')):	
		
		diff_in_bytes = len(values.encode('utf-8')) - len(values)	
		diff_ratio = sum(diff_ratios)/len(diff_ratios)
		
		average_length = int(sum(lengths)/len(lengths))

		#weighted average of avgLength and maxLength
		b=1.5
		average_length = (1+b**2)*(average_length*max(lengths))/((b**2)*average_length + max(lengths))
		
		double_width = any(x > 0.5  for x in diff_ratios)
		
		#avgLength
		if max(lengths_special) > 0.5*column_width and double_width == True: 
			new_column_width = 2*column_width
			width_changed = True
		
		elif int(average_length + column_width*diff_ratio) > int(0.6*column_width):
			coef = 2 + average_length/column_width
			
			if (max(diff_ratios)-diff_ratio)/diff_ratio > 2:
				diff_ratio = max(diff_ratios) 
			
			diff_width_percentage = diff_ratio*coef if diff_ratio*coef <= 1 else 1
			width_changed = True

			new_column_width = column_width + int(column_width*diff_width_percentage)
	
	return new_column_width, width_changed
	
	
	
'''
Converts National Character Varying to Varchar with recalculating column's width. 
'''	
def convert_nvarchar(line, table_name, conn):
	column_name, column_width = (part.strip() for part in line.split(' NATIONAL CHARACTER VARYING', 1))
	column_width = int(column_width.strip('(),'))
	new_column_width = 0
	width_changed = False
	
	query = 'select distinct length(%s), %s from %s order by 1 desc limit 15' %(column_name, column_name, table_name)

	cur = conn.cursor()
	result = cur.execute(query).fetchall()
	row_count = cur.rowcount
	cur.close()
	
	if row_count != 0: 

		lengths, values = list(map(list, zip(*result)))
		lengths = list(filter (lambda x: x is not None and x is not 0, lengths))
		values = list(filter (lambda x: x is not None and x is not '', values))
		
		print(column_name, lengths)
		
		if (len(lengths) > 0): 
			new_column_width, width_changed = recalculate_column_width(lengths, values, column_width)
			
			
	line = line.replace(' NATIONAL CHARACTER VARYING', ' VARCHAR', 1)
	
	if width_changed == True: 
		line = line.replace(str(column_width), str(new_column_width), 1)

	return line


	
'''
Converts distribution to segmentation using same column. Including kSafety level 1, segmented across all nodes. 
'''	
def convert_distribution(line):
	line = line.replace('DISTRIBUTE ON (', 'SEGMENTED BY HASH(', 1)
	line = line.replace(';', ' ALL NODES KSAFE 1\n', 1)

	return line
	

	

if __name__ == "__main__":

	default_conn = { 'DRIVER': '{NetezzaSQL}', 
					'SERVER': '***',
					'port': 5480,
					'database': '***',
					'user': '***',
					'password': '***'
					}

	schema_privileges = True
	lines_list = []
    output_file = 'ddlVertica.sql'
	
	'''
	Read required args.
	'''
	if len(sys.argv) > 1: 
		
		parser = argparse.ArgumentParser()
		
		parser.add_argument('--server', help='Name of the Netezza server.')
		parser.add_argument('--port', help='Netezza port number.')
		parser.add_argument('--database', help='Name of the Netezza database.')
		parser.add_argument('--user', help='Netezza user.')
		parser.add_argument('--password', help='Password for Netezza user. ')
		parser.add_argument('--file', help='File containing Netezza DDL. Include the .sql sufix.')
		
		args=parser.parse_args()
		
		if len(sys.argv) == 7: 
		
			conn_info = { 'DRIVER': '{NetezzaSQL}', 
					'SERVER': args.server,
					'port': args.port,
					'database': args.database,
					'user': args.user,
					'password': args.password
					}
					
			file_name = args.file				

			
		else: 
			print('Not all arguments provided. Try runing the script with \'-h\' for additional help.')
			sys.exit()

	else: 
		conn_info = default_conn			
		file_name = 'ddlNetezza.sql'
				
		print('No arguments provided. Default connection settings used and file name used.')
		
	
	
	'''
	Connect to database.
	'''
	try: 
		conn = connect_to_db()	
		
	except pyodbc.Error as err:
		print ('Connection to Db failed. Check your credentials.')
		sys.exit()
	 
	 
	'''
	Read DDL file. 
	'''
	try: 
		with open (file_name, 'r') as f:
			for line in f:				
                
				if 'CREATE TABLE' in line: 
					table_name = line.split('CREATE TABLE', 1)[1].strip()
			
				elif 'NATIONAL CHARACTER VARYING' in line: 
					line = convert_nvarchar(line, table_name, conn)					
					
				elif 'DISTRIBUTE ON' in line: 
					line = convert_distribution(line.rstrip())
					
					#optional - including schema privileges
					if schema_privileges == True: 
						lines_list.append(line)
						line = ('INCLUDE SCHEMA PRIVILEGES;')
			
				lines_list.append(line)
				
				
	except IOError: 
		print('Could not open the .sql file containing required DDL.')
		
			
	'''
	Close connection to database.
	'''
	conn.close()	
	
	
	'''
	Write to DDL file.
	'''
	try: 
		with open (output_file, 'w+') as f_out:	
			f_out.writelines(lines_list)
				
	except IOError: 
		print('Could not open the .sql file for writing required DDL.')

	

	
	