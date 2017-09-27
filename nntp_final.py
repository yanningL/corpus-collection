#!/usr/bin/python
# -*- coding: utf-8 -*-

# Import libraries
from nntplib import NNTP
import numpy as np
import os
import csv

######################################

def find_unique_subjects_and_authors(items_original):
    
    # Empty list
    items_reformatted = []

    # Create new list of tuples with only relevent details
    for message_number, subject, author, date, message_id, references, size, lines in items_original:
        # Remove "Re: " in subject line
        if subject[0:4] == "Re: ":
            subject = subject[4:]
        items_reformatted.append((message_number, subject, author))

    # Convert to numpy array
    dtype = [('message_number', int), ('subject', 'S40'), ('author', 'S40')]
    items_array = np.array(items_reformatted, dtype = dtype)

    # Sort by subject
    items_array_sort = np.sort(items_array, axis=0, order="subject")
        
    # Iterate through subjects to find unique subjects and authors
    subject_number = 0
    subject_current = '<null>'
    authors = []
    author_numbers = []
    items_array_new = []
    for item in items_array_sort:
        if item[1] != subject_current:
            subject_current = item[1]
            subject_number += 1
            authors = []
            author_numbers.append(0)
        if item[2] not in authors:
            authors.append(item[2])
            author_numbers[-1] += 1
        items_array_new.append((int(item[0]), subject_number, authors.index(item[2])+1))
        
    # Return array of unique subjects and authors
    return items_array_new, subject_number, author_numbers

######################################

def combine_conversations(items_to_combine, number_of_subjects):
    
    # Create blank array
    conversations = []
    for i in range(number_of_subjects):
        conversations.append('<s>')
    
    # Parse the message
    for message_number, subject_number, author_number in items_to_combine:
        
        # Read header and body
        try:
            resp, number, id, text = s.article(str(message_number))
            error = False
        except:
            print " -- -- -- EXCEPTION: NNTP Error caught [" + str(subject_number) + "] -- -- --"
            error = True
        
        # If successful read
        if error == False:
            
            # Determine encoding
            encoding = 'none'
            for line in text:
                if line[0:18] == 'Content-Type: text':
                    index = line.find('charset')
                    if index != -1:
                        encoding = line[index+8:]
                        end = min(encoding.find(';'), encoding.find(' '))
                        if end != -1:
                            encoding = encoding[0:end]
                        # print "DEBUG: line + " === " + encoding
            encoding2 = 'none'
            for line in text:
                if line[0:27] == 'Content-Transfer-Encoding: ':
                    encoding2 = line[27:]

            # print "DEBUG: line + " === " + encoding
            # print "-- Message [" + str(message_number) + "] Subject [" + str(subject_number) + "] Author [" + str(author_number) + "]" + " Encoding [" + encoding + "," + encoding2 + "]"

            # Setup variables to parse body
            header = True
            finish = False
            output = ""

            # Parse body of post
            try:
                for line_raw in text:
                    # Decode text into UTF-8
                    if encoding == 'none':
                        line = line_raw.encode('utf-8')
                    else:
                        line = line_raw.decode(encoding).encode('utf-8')
                    # Parse pre-signature limiter
                    if line[0:2] == "--":
                        finish = True    
                    # Add line if appropriate
                    if (header == False) and (finish == False) and (line[0:1] != '>'):
                        if (('wrote:' not in line) == True) and (('a écrit :' not in line) == True) and (('a écrit :' not in line) == True) and (len(line) > 0):
                            # print line
                            if len(output) == 0:
                                output = line
                            else:
                                if output[-1:] == ' ':
                                    output = output + line
                                else:
                                    output = output + " " + line                        
                    # Find end of header
                    if line == '':
                        header = False
            except UnicodeDecodeError:
                print " -- -- -- EXCEPTION: Unicode Decode Error caught [" + str(subject_number) + "] -- -- --"
            except LookupError:
                print " -- -- -- EXCEPTION: Lookup Error caught [" + str(subject_number) + "] -- -- --"
            #print "DEBUG: " + output[0:50]

            #print subject_number, author_number, output[0:39]
            conversations[subject_number - 1] += '<utt uid="' + str(author_number) + '">' + output + '</utt>'
            #print conversations[subject_number - 1]
            #print "DEBUG: " + output[0:40]

    # Insert end-limiter for conversations
    for i in range(number_of_subjects):
        conversations[i] += '</s>'

    return conversations

######################################

# Open news server
#s = NNTP('freenews.netfront.net', readermode=True)
s = NNTP('blaine.gmane.org', readermode=True)
#s = NNTP('news2.informatik.uni-stuttgart.de', readermode=True) - does not return groups
print "Opened connection to news server"

# Read pre-existing group list if available
if os.path.isfile('groups.txt'):
    french_groups = []
    with open('groups.txt') as f:
        for line in f:
            french_groups.append(line[:-1])
    print "- read " + str(len(french_groups)) + " French groups from file"
# Otherwise create from server
else: 
    # Read group list
    groups = s.list()
    print "- there are " + str(len(groups[1])) + " groups in total"

    # Create empty list for French groups
    french_groups = []

    # Find French groups
    for group in groups[1]:
        currgroup = group[0]
        #if currgroup[0:2] == 'fr':
        if 'french' in currgroup:
            french_groups.append(group[0])
    print "- there are " + str(len(french_groups)) + " groups in French"

    # Save French groups
    with open('groups.txt', 'w') as f:
        for group in french_groups:
            f.write(group + "\n")
    print "- written to file"

# Open file to write
f = open('samplegroup_fra.xml', 'w')
f.write('<dialog>\n')
f.close()

# Open file for statistics
g = open('stats_message.csv', 'wb')
group_writer = csv.writer(g)
group_writer.writerow(['Group', 'No. of messages', 'Mean authors', 'Max authors']) 
g.close()

# Iterate through French groups (only subset at present)
for group in french_groups[]:
    
    # Read number of messages in group
    resp, count, first, last, name = s.group(group)
    print "Group [" + group + "] has " + count + " articles (" + first + ", " + last + ")"
    
    # Skip empty newsgroups
    if count > 0:

        # Read items info from group
        print "- Reading items"
        
        # DEBUG - ******** THIS NEEDS TO BE REMOVED, IT JUST LOOKS AT LAST 50 MESSAGES TO SAVE TIME FOR NOW *********
        #if int(last)-int(first) > 200:
        #    first = str(int(last)-200)
        #    print "-- DEBUG: Truncating to (" + first + "," + last + ")"
        # DEBUG
        
        resp, items = s.xover(first, last)
		
        # Find unique subjects and authors
        print "- Sorting items"
        items_unique, subject_number, author_numbers = find_unique_subjects_and_authors(items)
        print "-- There are " + str(subject_number) + " unique subjects in this forum"
        
        # Write group, number of subjects, average and maximum number of authors
        g = open('stats_message.csv', 'ab')
        group_writer = csv.writer(g)
        group_writer.writerow([group, subject_number, np.mean(author_numbers), np.max(author_numbers)])
        g.close()
        
        # Combine conversations
        print "- Combining conversations"
        conversations = combine_conversations(items_unique, subject_number)
        
        # Create statistics file for each group
        hname="stats_author_"+group+".csv"
        h=open(hname,'wb')
        author_writer = csv.writer(h)
        author_writer.writerow(['Conversation no.', 'No. of authors'])
		
        # Write conversations and statistics
        f = open('samplegroup_fra.xml', 'a')
        index = 0
        counter = 1
        for dialog in conversations:
		if author_numbers[index] >= 2 and 'MIME' not in dialog and '"></utt>' not in dialog:
	        print "-- Writing conversation on subject " + str(index + 1)
	        f.write(dialog + '\n')
	        #print "DEBUG: " + dialog
	        author_writer.writerow([counter,author_numbers[index]])
	        counter += 1
		index += 1
        f.close()

        # Close statistics file
        h.close()
        
# Close file
f = open('samplegroup_fra.xml', 'a')
f.write('</dialog>\n')
f.close()
g.close()
