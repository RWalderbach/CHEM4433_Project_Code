# -*- coding: utf-8 -*-




from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QPushButton
import time
import pyperclip
import re
import mysql.connector
from selenium import webdriver


class Ui_CitationProject(object):
    # Generic URLs are used for concatenation and eventual URL navigation
    generic_url1 = 'https://okstate-stillwater.primo.exlibrisgroup.com/discovery/search?query=any,contains,'
    generic_url2 = '&tab=Everything&search_scope=MyInst_and_CI&vid=01OKSTATESTILL_OKSTAT:OKSTAT&offset=0'
    # Default Username
    username = 'rwalderbach'

    # Code largely only used for debugging. Takes in DOI code and returns citation info and whether it
    # has addition citation data
    def navToDOI(self, newDOI):
        # Needed for direct URL navigation
        newDOI.replace('/', '~2F')

        # Selenium Stuff Below
        driver.get(Ui_CitationProject.generic_url1 + newDOI + Ui_CitationProject.generic_url2)

        driver.refresh()

        time.sleep(2)

        searchResults = driver.find_element_by_tag_name("prm-brief-result-container")

        try:
            for element in searchResults:
                element.click()
                print("clicked")

        except:
            searchResults.click()

        time.sleep(2)
        driver.find_element_by_css_selector("#Citation").click()
        time.sleep(0.5)
        driver.find_element_by_xpath("//span[contains(text(),'MLA (8th edition)')]").click()
        time.sleep(0.5)
        driver.find_element_by_xpath("//button[@id='copy-citation-button']").click()

        citationInfo = pyperclip.paste()
        print(citationInfo)

        try:
            driver.find_element_by_xpath("//span[contains(text(),'cited in this')]").click()

            hasCited = True
            print(hasCited)

        except:
            hasCited = False
            print(hasCited)

        driver.save_screenshot("scrnsht.png")

        return citationInfo, hasCited

    # Main Workhorse function for gathering citation data. Takes in a DOI and a levelnumber and returns nothing
    # Directly interacts with the database
    def navToCitations(self, newDOI, levelNumber):
        # Puts together the username and table name, used for string formatting in SQL statements
        citationinfo = Ui_CitationProject.username + '_citationinfo'
        citationcount = Ui_CitationProject.username + '_citationcount'
        placeholderDOI = newDOI
        newDOI.replace('/', '~2F')

        # Selenium Stuff Below
        driver.get(Ui_CitationProject.generic_url1 + newDOI + Ui_CitationProject.generic_url2)

        driver.refresh()

        time.sleep(2)

        try:
            searchResults = driver.find_element_by_tag_name("prm-brief-result-container")

        except:
            # If DOI does not navigate correctly, delete it from the relevant table
            print("Something went wrong. It appears that a DOI cannot be found: " + newDOI)
            sql = "DELETE FROM {citationinfo} " \
                  "WHERE DOI = (%s)".format(citationinfo=citationinfo)
            val = placeholderDOI
            mycursor.execute(sql, (val,))
            return

        try:
            for element in searchResults:
                element.click()
                print("clicked")

        except:
            searchResults.click()

        time.sleep(2)

        try:
            driver.find_element_by_xpath("//span[contains(text(),'cited in this')]").click()

        except:
            # If Citations button is found, remove that flag from the table
            print("Something went wrong. It appears that a citation flag was set incorrectly for DOI" + newDOI)
            sql = "UPDATE {citationinfo} " \
                  "SET HasButton = 0 " \
                  "WHERE DOI = (%s)".format(citationinfo=citationinfo)
            val = placeholderDOI
            mycursor.execute(sql, (val,))
            return

        time.sleep(3)

        try:
            driver.find_element_by_tag_name("prm-brief-result-container").click()

        except:
            # If no citations are available, set that item to visited and move on
            print("Something went wrong. It appears that no results appeared for DOI" + newDOI)
            sql = "UPDATE {citationinfo} " \
                  "SET Visited = 1 " \
                  "WHERE DOI = (%s)".format(citationinfo=citationinfo)
            val = placeholderDOI
            mycursor.execute(sql, (val,))
            return

        count = 0

        try:
            # Main loop to navigate to each cited paper and pull ciation information
            while True:

                time.sleep(2)
                # Don't worry, I hate this too:
                driver.find_element_by_xpath(
                    "//body/primo-explore[1]/div[3]/div[1]/md-dialog[1]/md-dialog-content[1]/sticky-scroll[1]/prm-full-view[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/prm-full-view-service-container[1]/div[2]/prm-action-list[1]/md-nav-bar[1]/div[1]/nav[1]/ul[1]/div[1]/li[5]/button[1]/span[1]/div[1]/prm-icon[1]/md-icon[1]").click()

                time.sleep(0.5)
                driver.find_element_by_xpath("//span[contains(text(),'MLA (8th edition)')]").click()
                time.sleep(0.5)
                driver.find_element_by_xpath("//button[@id='copy-citation-button']").click()

                # Pull citation info from the clipboard
                citationInfo = pyperclip.paste()
                print(citationInfo)

                try:
                    driver.find_element_by_xpath("//span[contains(text(),'cited in this')]")

                    hasCited = True
                    print(hasCited)

                except:
                    hasCited = False
                    print(hasCited)

                time.sleep(3)
                if count == 0:
                    driver.find_element_by_xpath(
                        "//body/primo-explore[1]/div[3]/div[1]/button[2]/prm-icon[1]/md-icon[1]").click()

                else:

                    driver.find_element_by_xpath(
                        "//body/primo-explore[1]/div[3]/div[1]/button[3]/prm-icon[1]/md-icon[1]").click()

                count += 1

                # Convert citation info using Parser and pull relevant parameters out
                doi, author, title, journal, year = Ui_CitationProject.parseCitationIntoArray(self, citationInfo)

                if doi == -1:
                    continue

                try:
                    # Insert citation info into both citationinfo and citationcount tables using string formatting
                    print("attempting to insert: " + doi)
                    sql = "INSERT INTO {citationinfo} (LevelNumber, DOI, Authors, Title, Journal, Year,  HasButton, Visited) " \
                          "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)".format(citationinfo=citationinfo)

                    if hasCited:
                        val = (levelNumber, doi, author, title, journal, year, 1, 0)

                    else:
                        val = (levelNumber, doi, author, title, journal, year, 0, 0)

                    mycursor.execute(sql, val)
                    print("inserted.")

                    print("attempting to add to citation count: " + doi)
                    sql = "INSERT INTO {citationcount} (DOI, CitationCount) " \
                          "VALUES (%s, %s)".format(citationcount=citationcount)
                    val = (doi, 1)
                    mycursor.execute(sql, val)
                    print("added.")

                    mydb.commit()

                except Exception as e:
                    # If the citation DOI has already been encountered, increment citationcount
                    print(e)
                    sql = "UPDATE {citationcount} " \
                          "SET Count = Count + 1 " \
                          "WHERE DOI = (%s)".format(citationcount=citationcount)
                    val = '\'' + doi + '\''
                    mycursor.execute(sql, val)


        except Exception as e:
            print(e)
            print("exited at count: " + str(count))

    # Main function that builds the web
    def iterativeCitationFind(self):
        citationinfo = Ui_CitationProject.username + '_citationinfo'
        attemptCount = 0
        # range is largely arbitray. If this ever hits 100, the algo has probably broken
        for x in range(100):
            try:
                # Pull DOIs that correspond to hasButton but not visited
                sql = "SELECT DOI " \
                      "FROM {citationinfo} " \
                      "WHERE HasButton = 1 " \
                      "AND Visited = 0 " \
                      "ORDER BY LevelNumber".format(citationinfo=citationinfo)

                mycursor.execute(sql)

                results = mycursor.fetchall()

                print("Here are the DOIs to be iterated through:")
                for doiResult in results:
                    newDOI = str(doiResult).replace("'", '')[1:-2]
                    print(str(newDOI))

                # for each doi returned by query, pass it to navToCitations to actually add citation info
                for doiResult in results:

                    newDOI = str(doiResult).replace("'", '')[1:-2]

                    Ui_CitationProject.navToCitations(self, newDOI, attemptCount)

                    try:
                        sql = "UPDATE {citationinfo} " \
                              "SET Visited = 1 " \
                              "WHERE DOI = (%s)".format(citationinfo=citationinfo)
                        val = doiResult

                        mycursor.execute(sql, val)

                    except Exception as e:
                        print(e)
                        print("Something happened when trying to set to Visited.")


            except:
                print(attemptCount)
                attemptCount += 1
                if (attemptCount > 10):
                    return

    # Function used to convert raw MLA 8th Edition citations into useful parameters
    def parseCitationIntoArray(self, citation):
        # Find indexes based on certain substrings
        firstQuote = citation.find('“')
        secondQuote = citation.find('”')
        doiIndex = citation.find('doi:')

        author = citation[0:firstQuote].strip()
        title = citation[firstQuote:(secondQuote + 1)]
        journal = citation[(secondQuote + 1):citation.find(',', secondQuote)].strip()
        year = re.search('(19|20)\d{2},', citation).group(0)[:-1]
        if doiIndex == -1:
            doi = -1

        else:
            doi = citation[(doiIndex + 4):-3]

        print(author)
        print(title)
        print(journal)
        print(year)
        print(doi)

        return doi, author, title, journal, year

    # Function takes a DOI and adds the paper tio
    def addPaperToStart(self, newDOI):
        citationinfo = Ui_CitationProject.username + '_citationinfo'
        papersread = Ui_CitationProject.username + '_papersread'

        try:
            rawCitation, tag = Ui_CitationProject.navToDOI(self, newDOI)
            doi, author, title, journal, year = Ui_CitationProject.parseCitationIntoArray(self, rawCitation)

        except Exception as e:
            print(e)

        try:
            # Add the paper to papersRead
            sql = "INSERT INTO {papersread} (DOI, RelevanceRating) " \
                  "VALUES (%s, %s)".format(papersread=papersread)
            val = (doi, 5)

            mycursor.execute(sql, val)

            mydb.commit()

        except Exception as e:
            print(e)
            return -1

        try:
            # Add the paper to citationsInfo
            sql = "INSERT INTO {citationinfo} (LevelNumber, DOI, Authors, Title, Journal, Year, HasButton, Visited) " \
                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)".format(citationinfo=citationinfo)
            val = (-1, doi, author, title, journal, year, tag, 0)

            mycursor.execute(sql, val)

            mydb.commit()

        except Exception as e:
            print(e)
            return -1

    # Takes username and return username as a means to confirm username existence
    def findExistingUser(self, username):
        try:
            sql = "SELECT username FROM user " \
                  "WHERE username = (%s)"
            val = username

            mycursor.execute(sql, (val,))

            result = mycursor.fetchall()

            return result[0][0]

        except Exception as e:
            print(e)
            print("No user with that username.")
            return -1

    # Didn't end up needing this one
    def changeUsers(self):
        print("MISSING CODE: changeUsers")

    # Takes in username and interests and adds a new user into user table and creates tables specifically for that user
    def addUser(self, newUsername, interest1, interest2, interest3):

        citationinfo = newUsername + '_citationinfo'
        citationcount = newUsername + '_citationcount'
        papersread = newUsername + '_papersread'

        try:
            sql = "INSERT INTO User (Username, Interest1, Interest2, Interest3) VALUES (%s, %s, %s, %s)"
            val = (newUsername, interest1, interest2, interest3)

            mycursor.execute(sql, val)

            mydb.commit()

        except:
            return -1

        sql = "CREATE TABLE IF NOT EXISTS {citationinfo} (" \
              "LevelNumber INT NULL, " \
              "DOI VARCHAR(200) NOT NULL, " \
              "Authors VARCHAR(200) NULL, " \
              "Title LONGTEXT NULL, " \
              "Journal LONGTEXT NULL, " \
              "Year INT NULL, " \
              "HasButton TINYINT NULL, " \
              "Visited TINYINT NULL, " \
              "PRIMARY KEY (DOI))".format(citationinfo=citationinfo)

        mycursor.execute(sql)

        mydb.commit()

        sql = "CREATE TABLE IF NOT EXISTS {papersread} (" \
              "`DOI` VARCHAR(60) NOT NULL, " \
              "`RelevanceRating` INT NULL, " \
              "PRIMARY KEY (`DOI`))".format(papersread=papersread)

        mycursor.execute(sql)

        mydb.commit()

        sql = "CREATE TABLE IF NOT EXISTS {citationcount} (" \
              "`DOI` VARCHAR(60) NOT NULL, " \
              "`CitationCount` INT NULL, " \
              "PRIMARY KEY (`DOI`))".format(citationcount=citationcount)

        mycursor.execute(sql)

        mydb.commit()

        # These Schema didn't end up working as intended, Keeping them here for clarity

        # sql = "CREATE TABLE IF NOT EXISTS {papersread} (" \
        #      "`DOI` VARCHAR(60) NOT NULL, " \
        #      "`RelevanceRating` INT NULL, " \
        #      "INDEX %s (`DOI` ASC) " \
        #      "PRIMARY KEY (`DOI`), " \
        #      "CONSTRAINT %s " \
        #      "FOREIGN KEY (`DOI`) " \
        #      "REFERENCES {citationinfo} (`DOI`) " \
        #      "ON DELETE CASCADE " \
        #      "ON UPDATE CASCADE)".format(papersread=papersread, citationinfo=citationinfo)

        # constraint = newUsername + '_fk_papers read_citation info1'
        # index = newUsername + '_fk_papers read_citation info1_idx'

        # val = (constraint, index)

        # mycursor.execute(sql, val)

        # index = newUsername + '_fk_citation = count_citation info_idx'
        # constraint = newUsername + '_fk_citation count_citation info'

        # sql = "CREATE TABLE IF NOT EXISTS {citationcount} (" \
        #      "`DOI` VARCHAR(60) NOT NULL, " \
        #      "`CitationCount` INT NULL, " \
        #      "INDEX {'index'} (`DOI` ASC)," \
        #      "PRIMARY KEY (`DOI`)," \
        #      "CONSTRAINT {'constraint'}" \
        #      "FOREIGN KEY (`DOI`)" \
        #      "REFERENCES {citationinfo} (`DOI`)" \
        #      "ON DELETE CASCADE " \
        #      "ON UPDATE CASCADE)".format(citationcount=citationcount, index=index, constraint=constraint, citationinfo=citationinfo)

        # val = (index, constraint)

    # Takes no arguments, no return. Deletes everything from a user's citationinfo and citationcount tables
    def clearWebFunction(self):
        citationinfo = Ui_CitationProject.username + '_citationinfo'
        citationcount = Ui_CitationProject.username + '_citationcount'

        sql = "DELETE FROM {citationinfo} " \
              "WHERE levelnumber > -1".format(citationinfo=citationinfo)

        mycursor.execute(sql)
        mydb.commit()

        sql = "DELETE FROM {citationcount}".format(citationcount=citationcount)

        mycursor.execute(sql)
        mydb.commit()

    # Selects DOIs from papersRead table for user and returns them as iterable
    def showReadPapers(self):
        papersread = Ui_CitationProject.username + '_papersread'

        try:
            sql = "SELECT DOI " \
                  "FROM {papersread}".format(papersread=papersread)

            mycursor.execute(sql)

            results = mycursor.fetchall()

            return results

        except Exception as e:
            print(e)

    # Pulls interests from user table and compares them against titles in citationinfo, and takes count of returned results
    # returns a tuple with count and results iterable
    def showRecommendedPapers(self):
        papersread = Ui_CitationProject.username + '_papersread'
        citationinfo = Ui_CitationProject.username + '_citationinfo'

        try:
            sql = "SELECT Interest1, Interest2, Interest3 " \
                  "FROM User " \
                  "WHERE Username = (%s)"

            val = (Ui_CitationProject.username,)

            mycursor.execute(sql, val)

            result = mycursor.fetchall()

            interest1, interest2, interest3 = result[0][0], result[0][1], result[0][2]

        except Exception as e:
            print(e)

        try:
            sql = "SELECT DOI, Title, Authors, Journal, Year " \
                  "FROM {citationinfo} " \
                  "WHERE Title LIKE CONCAT('%',(%s),'%') " \
                  "OR Title LIKE CONCAT('%',(%s),'%') " \
                  "OR Title LIKE CONCAT('%',(%s),'%')".format(citationinfo=citationinfo)

            val = (interest1, interest2, interest3)

            mycursor.execute(sql, val)

            results = mycursor.fetchall()


            sql = "SELECT COUNT(*) " \
                  "FROM " \
                  "(SELECT DOI, Title, Authors, Journal, Year " \
                  "FROM {citationinfo} " \
                  "WHERE Title LIKE CONCAT('%',(%s),'%') " \
                  "OR Title LIKE CONCAT('%',(%s),'%') " \
                  "OR Title LIKE CONCAT('%',(%s),'%'))" \
                  "AS matched".format(citationinfo=citationinfo)

            val = (interest1, interest2, interest3)

            mycursor.execute(sql, val)

            count = mycursor.fetchall()

            return count, results

        except Exception as e:
            print(e)

    # Takes year1 and year2 arguments, Selects citation details for papers with year in range
    # Returns tuple with count and results iterable
    def showPapersInRange(self, year1, year2):
        citationinfo = Ui_CitationProject.username + '_citationinfo'

        try:
            sql = "SELECT DOI, Title, Year FROM {citationinfo} " \
                  "WHERE Year >= (%s) AND Year <= (%s) " \
                  "ORDER BY Year".format(citationinfo=citationinfo)

            val = (year1, year2)

            mycursor.execute(sql, val)

            results = mycursor.fetchall()

            sql = "SELECT COUNT(*) " \
                  "FROM " \
                  "(SELECT DOI, Title, Year FROM {citationinfo} " \
                  "WHERE Year >= (%s) AND Year <= (%s) " \
                  "ORDER BY Year) " \
                  "AS matched".format(citationinfo=citationinfo)

            val = (year1, year2)

            mycursor.execute(sql, val)

            count = mycursor.fetchall()

            return count, results


        except Exception as e:
            print(e)

    # Takes username1 and username2 as arguments, joins both user's citationinfo tables on DOI to find commonality
    # Returns tuple of count and results iterable
    def showSharedPapers(self, username1, username2):
        citationinfo1 = username1 + '_citationinfo'
        citationinfo2 = username2 + '_citationinfo'

        try:
            sql = "SELECT t1.DOI, t1.Title " \
                  "FROM {citationinfo1} as t1 " \
                  "INNER JOIN {citationinfo2} as t2 " \
                  "ON t1.DOI = t2.DOI".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

            mycursor.execute(sql)

            results = mycursor.fetchall()

            sql = "SELECT COUNT(*) " \
                  "FROM " \
                  "(SELECT t1.DOI, t1.Title " \
                  "FROM {citationinfo1} as t1 " \
                  "INNER JOIN {citationinfo2} as t2 " \
                  "ON t1.DOI = t2.DOI)" \
                  "AS matched".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

            mycursor.execute(sql)

            count = mycursor.fetchall()

            return count, results

        except Exception as e:
            print(e)

    # Takes usrename1 and username2 as parameters and makes union to Select all papers between the two
    # Returns tuple of count and results iterable
    def showAllPapers(self, username1, username2):
        citationinfo1 = username1 + '_citationinfo'
        citationinfo2 = username2 + '_citationinfo'

        try:
            sql = "SELECT DOI, Title " \
                  "FROM {citationinfo1} " \
                  "UNION DISTINCT " \
                  "SELECT DOI, Title " \
                  "FROM {citationinfo2}".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

            mycursor.execute(sql)

            results = mycursor.fetchall()

            sql = "SELECT COUNT(*) " \
                  "FROM " \
                  "(SELECT DOI, Title " \
                  "FROM {citationinfo1} " \
                  "UNION DISTINCT " \
                  "SELECT DOI, Title " \
                  "FROM {citationinfo2})" \
                  "AS total".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

            mycursor.execute(sql)

            count = mycursor.fetchall()

            return count, results

        except Exception as e:
            print(e)

    # Boring PyQt5 layout stuff.
    def setupUi(self, CitationProject):
        CitationProject.setObjectName("CitationProject")
        CitationProject.resize(1222, 851)
        self.centralwidget = QtWidgets.QWidget(CitationProject)
        self.centralwidget.setObjectName("centralwidget")
        self.addUser_text = QtWidgets.QTextEdit(self.centralwidget)
        self.addUser_text.setGeometry(QtCore.QRect(650, 110, 291, 31))
        self.addUser_text.setObjectName("addUser_text")

        self.addUser_button = QtWidgets.QPushButton(self.centralwidget)
        self.addUser_button.setGeometry(QtCore.QRect(960, 180, 131, 61))
        self.addUser_button.setObjectName("addUser_button")
        self.addUser_button.clicked.connect(self.addUserButtonClick)

        self.readPaper_browser = QtWidgets.QTextBrowser(self.centralwidget)
        self.readPaper_browser.setGeometry(QtCore.QRect(40, 110, 421, 201))
        self.readPaper_browser.setObjectName("readPaper_browser")

        self.readPapers_label = QtWidgets.QLabel(self.centralwidget)
        self.readPapers_label.setGeometry(QtCore.QRect(120, 80, 101, 20))
        self.readPapers_label.setObjectName("readPapers_label")

        self.readPapers_button = QtWidgets.QPushButton(self.centralwidget)
        self.readPapers_button.setGeometry(QtCore.QRect(470, 110, 111, 41))
        self.readPapers_button.setObjectName("readPapers_button")
        self.readPapers_button.clicked.connect(self.addPapersToWebButtonClick)


        self.clearWeb = QtWidgets.QPushButton(self.centralwidget)
        self.clearWeb.setGeometry(QtCore.QRect(480, 260, 111, 41))
        self.clearWeb.setObjectName("clearWeb")
        self.clearWeb.clicked.connect(self.clearWebButtonClick)


        self.showPapers_button = QtWidgets.QPushButton(self.centralwidget)
        self.showPapers_button.setGeometry(QtCore.QRect(560, 330, 221, 41))
        self.showPapers_button.clicked.connect(self.showRecommendedPapersButtonClick)


        font = QtGui.QFont()
        font.setPointSize(12)

        self.showPapers_button.setFont(font)
        self.showPapers_button.setObjectName("showPapers_button")

        self.year2_text = QtWidgets.QTextEdit(self.centralwidget)
        self.year2_text.setGeometry(QtCore.QRect(1070, 430, 81, 31))
        self.year2_text.setObjectName("year2_text")

        self.year1_text = QtWidgets.QTextEdit(self.centralwidget)
        self.year1_text.setGeometry(QtCore.QRect(960, 430, 81, 31))
        self.year1_text.setObjectName("year1_text")

        self.year1_label = QtWidgets.QLabel(self.centralwidget)
        self.year1_label.setGeometry(QtCore.QRect(990, 410, 91, 16))
        self.year1_label.setObjectName("year1_label")

        self.year2_label = QtWidgets.QLabel(self.centralwidget)
        self.year2_label.setGeometry(QtCore.QRect(1090, 410, 47, 13))
        self.year2_label.setObjectName("year2_label")

        self.interest1_text = QtWidgets.QTextEdit(self.centralwidget)
        self.interest1_text.setGeometry(QtCore.QRect(650, 190, 291, 31))
        self.interest1_text.setObjectName("interest1_text")

        self.interest2_label = QtWidgets.QTextEdit(self.centralwidget)
        self.interest2_label.setGeometry(QtCore.QRect(650, 230, 291, 31))
        self.interest2_label.setObjectName("interest2_label")

        self.interest3_label = QtWidgets.QTextEdit(self.centralwidget)
        self.interest3_label.setGeometry(QtCore.QRect(650, 270, 291, 31))
        self.interest3_label.setObjectName("interest3_label")

        self.interests_label = QtWidgets.QLabel(self.centralwidget)
        self.interests_label.setGeometry(QtCore.QRect(760, 160, 141, 21))
        self.interests_label.setObjectName("interests_label")

        self.scrollArea = QtWidgets.QScrollArea(self.centralwidget)
        self.scrollArea.setGeometry(QtCore.QRect(50, 390, 881, 401))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")

        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 879, 399))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")

        self.results_tableView = QtWidgets.QTextBrowser(self.scrollAreaWidgetContents_2)
        self.results_tableView.setGeometry(QtCore.QRect(0, 0, 879, 399))
        self.results_tableView.setMouseTracking(True)
        self.results_tableView.setObjectName("results_tableView")

        # These weren't needed and made the layout confusing
        #self.hScrollBar = QtWidgets.QScrollBar(self.scrollAreaWidgetContents_2)
        #self.hScrollBar.setGeometry(QtCore.QRect(0, 380, 881, 16))
        #self.hScrollBar.setOrientation(QtCore.Qt.Horizontal)
        #self.hScrollBar.setObjectName("hScrollBar")

        #self.vScrollBar = QtWidgets.QScrollBar(self.scrollAreaWidgetContents_2)
        #self.vScrollBar.setGeometry(QtCore.QRect(860, -1, 20, 381))
        #self.vScrollBar.setOrientation(QtCore.Qt.Vertical)
        #self.vScrollBar.setObjectName("vScrollBar")

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.addPaper_text = QtWidgets.QTextEdit(self.centralwidget)
        self.addPaper_text.setGeometry(QtCore.QRect(40, 40, 261, 31))
        self.addPaper_text.setObjectName("addPaper_text")

        self.addPaper_label = QtWidgets.QLabel(self.centralwidget)
        self.addPaper_label.setGeometry(QtCore.QRect(120, 20, 161, 16))
        self.addPaper_label.setObjectName("addPaper_label")

        self.addTable_button = QtWidgets.QPushButton(self.centralwidget)
        self.addTable_button.setGeometry(QtCore.QRect(320, 40, 75, 23))
        self.addTable_button.setObjectName("addTable_button")
        self.addTable_button.clicked.connect(self.addPaperButtonClick)


        self.results_label = QtWidgets.QLabel(self.centralwidget)
        self.results_label.setGeometry(QtCore.QRect(450, 340, 101, 31))

        font = QtGui.QFont()
        font.setPointSize(14)

        self.results_label.setFont(font)
        self.results_label.setObjectName("results_label")

        self.addUser_label = QtWidgets.QLabel(self.centralwidget)
        self.addUser_label.setGeometry(QtCore.QRect(760, 90, 81, 16))
        self.addUser_label.setObjectName("addUser_label")

        self.findUser_text = QtWidgets.QTextEdit(self.centralwidget)
        self.findUser_text.setGeometry(QtCore.QRect(650, 40, 291, 31))
        self.findUser_text.setObjectName("findUser_text")

        self.findUser_label = QtWidgets.QLabel(self.centralwidget)
        self.findUser_label.setGeometry(QtCore.QRect(740, 20, 111, 16))
        self.findUser_label.setObjectName("findUser_label")

        self.findUser_button = QtWidgets.QPushButton(self.centralwidget)
        self.findUser_button.setGeometry(QtCore.QRect(960, 40, 81, 31))
        self.findUser_button.setObjectName("findUser_button")
        self.findUser_button.clicked.connect(self.existingUserButtonClick)


        self.sharedUser1_text = QtWidgets.QTextEdit(self.centralwidget)
        self.sharedUser1_text.setGeometry(QtCore.QRect(1010, 520, 201, 31))
        self.sharedUser1_text.setObjectName("sharedUser1_text")

        self.sharedUser2_text = QtWidgets.QTextEdit(self.centralwidget)
        self.sharedUser2_text.setGeometry(QtCore.QRect(1010, 560, 201, 31))
        self.sharedUser2_text.setObjectName("sharedUser2_text")

        self.showRange_button = QtWidgets.QPushButton(self.centralwidget)
        self.showRange_button.setGeometry(QtCore.QRect(970, 380, 171, 23))
        self.showRange_button.setObjectName("showRange_button")
        self.showRange_button.clicked.connect(self.showPapersInRangeButtonClick)


        self.showShared_button = QtWidgets.QPushButton(self.centralwidget)
        self.showShared_button.setGeometry(QtCore.QRect(960, 480, 201, 23))
        self.showShared_button.setObjectName("showShared_button")
        self.showShared_button.clicked.connect(self.showSharedPapersButtonClick)


        self.sharedUser1_label = QtWidgets.QLabel(self.centralwidget)
        self.sharedUser1_label.setGeometry(QtCore.QRect(960, 530, 47, 13))
        self.sharedUser1_label.setObjectName("sharedUser1_label")

        self.sharedUser2_label = QtWidgets.QLabel(self.centralwidget)
        self.sharedUser2_label.setGeometry(QtCore.QRect(960, 570, 47, 13))
        self.sharedUser2_label.setObjectName("sharedUser2_label")

        self.showAllPapers_button = QtWidgets.QPushButton(self.centralwidget)
        self.showAllPapers_button.setGeometry(QtCore.QRect(960, 630, 201, 23))
        self.showAllPapers_button.setObjectName("showAllPapers_button")
        self.showAllPapers_button.clicked.connect(self.showAllPapersButtonClick)


        self.allPapersUser2_text = QtWidgets.QTextEdit(self.centralwidget)
        self.allPapersUser2_text.setGeometry(QtCore.QRect(1010, 710, 201, 31))
        self.allPapersUser2_text.setObjectName("allPapersUser2_text")

        self.allPapersUser1_label = QtWidgets.QLabel(self.centralwidget)
        self.allPapersUser1_label.setGeometry(QtCore.QRect(960, 680, 47, 13))
        self.allPapersUser1_label.setObjectName("allPapersUser1_label")

        self.allPapersUser2_label = QtWidgets.QLabel(self.centralwidget)
        self.allPapersUser2_label.setGeometry(QtCore.QRect(960, 720, 47, 13))
        self.allPapersUser2_label.setObjectName("allPapersUser2_label")

        self.allPapersUser1_text = QtWidgets.QTextEdit(self.centralwidget)
        self.allPapersUser1_text.setGeometry(QtCore.QRect(1010, 670, 201, 31))
        self.allPapersUser1_text.setObjectName("allPapersUser1_text")

        self.textBrowser = QtWidgets.QTextBrowser(self.centralwidget)
        self.textBrowser.setGeometry(QtCore.QRect(290, 340, 121, 31))
        self.textBrowser.setObjectName("textBrowser")

        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(190, 350, 91, 21))
        self.label.setObjectName("label")

        CitationProject.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(CitationProject)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1222, 21))
        self.menubar.setObjectName("menubar")

        CitationProject.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(CitationProject)
        self.statusbar.setObjectName("statusbar")
        CitationProject.setStatusBar(self.statusbar)

        self.retranslateUi(CitationProject)
        QtCore.QMetaObject.connectSlotsByName(CitationProject)

    # More PyQt5 stuff
    def retranslateUi(self, CitationProject):
        _translate = QtCore.QCoreApplication.translate
        CitationProject.setWindowTitle(_translate("CitationProject", "Citation Project"))
        self.addUser_button.setText(_translate("CitationProject", "Enter New User"))
        self.readPapers_label.setText(_translate("CitationProject", "Read Papers"))
        self.readPapers_button.setText(_translate("CitationProject", "Add Papers to Web"))
        self.clearWeb.setText(_translate("CitationProject", "Clear Web"))
        self.showPapers_button.setText(_translate("CitationProject", "Show Recommended Papers"))
        self.year1_label.setText(_translate("CitationProject", "Year            to"))
        self.year2_label.setText(_translate("CitationProject", "Year"))
        self.interests_label.setText(_translate("CitationProject", "Interests"))
        self.addPaper_label.setText(_translate("CitationProject", "Add Paper (DOI)"))
        self.addTable_button.setText(_translate("CitationProject", "Enter"))
        self.results_label.setText(_translate("CitationProject", "Results"))
        self.addUser_label.setText(_translate("CitationProject", "Add User"))
        self.findUser_label.setText(_translate("CitationProject", "Find Existing User"))
        self.findUser_button.setText(_translate("CitationProject", "Enter"))
        self.showRange_button.setText(_translate("CitationProject", "Show Papers Within Range"))
        self.showShared_button.setText(_translate("CitationProject", "Show Papers Shared Between Users"))
        self.sharedUser1_label.setText(_translate("CitationProject", "User 1:"))
        self.sharedUser2_label.setText(_translate("CitationProject", "User 2:"))
        self.showAllPapers_button.setText(_translate("CitationProject", "Show All Papers Between Users"))
        self.allPapersUser1_label.setText(_translate("CitationProject", "User 1:"))
        self.allPapersUser2_label.setText(_translate("CitationProject", "User 2:"))
        self.label.setText(_translate("CitationProject", "Amount of Papers:"))

    # Connector function for existing user button. Performs the actions that need to happen on click
    def existingUserButtonClick(self):
        # Pull username from field and check it against the database
        usernameText = self.findUser_text.toPlainText()

        setUsername = self.findExistingUser(usernameText)

        # Pushes text to field if no user of that name is found
        if  setUsername == -1:
            self.findUser_text.setPlainText("No User Found")

        # Clear text fields and push readpapers and interests to relevant fields
        else:
            Ui_CitationProject.username = setUsername
            self.addPaper_text.clear()
            self.readPaper_browser.clear()
            self.addUser_text.clear()
            self.interest1_text.clear()
            self.interest2_label.clear()
            self.interest3_label.clear()
            self.textBrowser.clear()
            self.year1_text.clear()
            self.year2_text.clear()
            self.sharedUser1_text.clear()
            self.sharedUser2_text.clear()
            self.allPapersUser1_text.clear()
            self.allPapersUser2_text.clear()
            self.results_tableView.clear()

            try:
                results = self.showReadPapers()

                for result in results:
                    self.readPaper_browser.append(result[0])

            except Exception as e:
                print(e)

            try:
                sql = "SELECT Interest1, Interest2, Interest3 " \
                      "FROM User " \
                      "WHERE Username = (%s)"

                val = Ui_CitationProject.username

                mycursor.execute(sql, (val,))

                interests = mycursor.fetchall()

                interest1 = interests[0][0]
                interest2 = interests[0][1]
                interest3 = interests[0][2]

                self.interest1_text.setText(interest1)
                self.interest2_label.setText(interest2)
                self.interest3_label.setText(interest3)
                
            except Exception as e:
                print(e)


            print(setUsername)
            print(Ui_CitationProject.username)

    # Connects addUser Button to relevant functions
    def addUserButtonClick(self):
        # pull username and interests from fields and create new user
        newUser = self.addUser_text.toPlainText()
        interest1 = self.interest1_text.toPlainText()
        interest2 = self.interest2_label.toPlainText()
        interest3 = self.interest3_label.toPlainText()

        status = self.addUser(newUser, interest1, interest2, interest3)

        if status == -1:
            newUser = self.addUser_text.setText('That User Already Exists.')

    # Connects addPaper Button to relevant functions
    def addPaperButtonClick(self):
        # Pulls newDOI from field and attempts to add it to readpapers table
        newDOI = self.addPaper_text.toPlainText()

        if self.addPaperToStart(newDOI) == -1:
            self.addPaper_text.setText('This paper is already in the list.')

        try:
            results = self.showReadPapers()

            for result in results:
                self.readPaper_browser.append(result[0])

        except Exception as e:
            print(e)

    # Connects addPapersToWeb Button to relevant functions
    def addPapersToWebButtonClick(self):
        # State based function performed each time
        self.iterativeCitationFind()

    # Connects clear web Button to relevant functions
    def clearWebButtonClick(self):
        # State based function performed each time
        self.clearWebFunction()

    # Connects Show Recommended Papers Button to relevant functions
    def showRecommendedPapersButtonClick(self):
        # Clears the table then pulls results from function and deisplays to relevant fields
        self.results_tableView.clear()

        try:
            count, results = self.showRecommendedPapers()

            self.textBrowser.setText(str(count[0][0]))

            for result in results:
                self.results_tableView.append(str(result))

        except Exception as e:
            print(e)

    # Connects Show Papers in Range Button to relevant functions
    def showPapersInRangeButtonClick(self):
        # Clears Table, and pulls years from fields and prints results to relevant fields
        self.results_tableView.clear()
        year1 = int(self.year1_text.toPlainText())
        year2 = int(self.year2_text.toPlainText())

        try:
            count, results = self.showPapersInRange(year1, year2)

            self.textBrowser.setText(str(count[0][0]))

            for result in results:
                self.results_tableView.append(str(result))

        except Exception as e:
            print(e)

    # Connects Show Shared Papers Button to relevant functions
    def showSharedPapersButtonClick(self):
        # Clears table and pulls usernames from fields, prints results to relevant fields
        self.results_tableView.clear()
        username1 = self.sharedUser1_text.toPlainText()
        username2 = self.sharedUser2_text.toPlainText()

        try:
            count, results = self.showSharedPapers(username1, username2)

            self.textBrowser.setText(str(count[0][0]))

            for result in results:
                self.results_tableView.append(str(result))

        except Exception as e:
            print(e)

    # Connects Show All Papers Button to relevant functions
    def showAllPapersButtonClick(self):
        # Clears table and pulls usernames from fields, prints results to relevant fields
        self.results_tableView.clear()
        username1 = self.allPapersUser1_text.toPlainText()
        username2 = self.allPapersUser2_text.toPlainText()

        try:
            count, results = self.showAllPapers(username1, username2)

            self.textBrowser.setText(str(count[0][0]))

            for result in results:
                self.results_tableView.append(str(result))

        except Exception as e:
            print(e)


# MAIN METHOD
if __name__ == "__main__":
    import sys

    # sets up virtual browser
    driver = webdriver.Chrome()

    # Connects to database and stores as parameter
    mydb = mysql.connector.connect(
        host="localhost",
        user="RWalderbach",
        password="SQLPassword19",
        database="demodatabase"
    )

    mycursor = mydb.cursor()

    # PyQt5 stuff
    app = QtWidgets.QApplication(sys.argv)
    CitationProject = QtWidgets.QMainWindow()
    ui = Ui_CitationProject()
    ui.setupUi(CitationProject)
    CitationProject.show()
    #ui.iterativeCitationFind()


    sys.exit(app.exec_())
