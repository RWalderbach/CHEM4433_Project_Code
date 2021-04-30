import time
import pyperclip
import re
import mysql.connector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import os

okstate_url = 'https://library.okstate.edu/'
generic_url1 = 'https://okstate-stillwater.primo.exlibrisgroup.com/discovery/search?query=any,contains,'
generic_url2 = '&tab=Everything&search_scope=MyInst_and_CI&vid=01OKSTATESTILL_OKSTAT:OKSTAT&offset=0'
username = 'hhassan'


#
# THE MAJORITY OF THE FOLLOWING IS LEGACY CODE AND IS UNCOMMENTED. MOST OF THIS IS PRESENT IN THE FINAL PROJECT
# IN ONE FORM OR ANOTHER, BUT ANY COMMENTS TO ITS RELEVANCE AND FUNCTION ARE MADE IN THE FINAL PROJECT CODE.
#

def navToDOI(newDOI):
    newDOI.replace('/', '~2F')
    driver.get(generic_url1 + newDOI + generic_url2)

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


def navToCitations(newDOI, levelNumber):
    citationinfo = username + '_citationinfo'
    citationcount = username + '_citationcount'
    placeholderDOI = newDOI
    newDOI.replace('/', '~2F')
    driver.get(generic_url1 + newDOI + generic_url2)

    driver.refresh()

    time.sleep(2)

    try:
        searchResults = driver.find_element_by_tag_name("prm-brief-result-container")

    except:
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
        print("Something went wrong. It appears that no results appeared for DOI" + newDOI)
        sql = "UPDATE {citationinfo} " \
              "SET Visited = 1 " \
              "WHERE DOI = (%s)".format(citationinfo=citationinfo)
        val = placeholderDOI
        mycursor.execute(sql, (val,))
        return

    count = 0

    try:
        while True:

            time.sleep(2)
            driver.find_element_by_xpath(
                "//body/primo-explore[1]/div[3]/div[1]/md-dialog[1]/md-dialog-content[1]/sticky-scroll[1]/prm-full-view[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/prm-full-view-service-container[1]/div[2]/prm-action-list[1]/md-nav-bar[1]/div[1]/nav[1]/ul[1]/div[1]/li[5]/button[1]/span[1]/div[1]/prm-icon[1]/md-icon[1]").click()

            time.sleep(0.5)
            driver.find_element_by_xpath("//span[contains(text(),'MLA (8th edition)')]").click()
            time.sleep(0.5)
            driver.find_element_by_xpath("//button[@id='copy-citation-button']").click()

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

            doi, author, title, journal, year = parseCitationIntoArray(citationInfo)

            if doi == -1:
                continue

            try:
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
                print(e)
                sql = "UPDATE {citationcount} " \
                      "SET Count = Count + 1 " \
                      "WHERE DOI = (%s)".format(citationcount=citationcount)
                val = '\'' + doi + '\''
                mycursor.execute(sql, val)


    except Exception as e:
        print(e)
        print("exited at count: " + str(count))


def iterativeCitationFind():
    citationinfo = username + '_citationinfo'
    attemptCount = 0
    for x in range(1000):
        try:
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

            for doiResult in results:

                newDOI = str(doiResult).replace("'", '')[1:-2]

                navToCitations(newDOI, attemptCount)

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


def parseCitationIntoArray(citation):
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


def addPaperToStart(newDOI):
    citationinfo = username + '_citationinfo'
    papersread = username + '_papersread'

    rawCitation, tag = navToDOI(newDOI)
    doi, author, title, journal, year = parseCitationIntoArray(rawCitation)

    try:
        sql = "INSERT INTO {citationinfo} (LevelNumber, DOI, Authors, Title, Journal, Year, HasButton, Visited) " \
              "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)".format(citationinfo=citationinfo)
        val = (-1, doi, author, title, journal, year, tag, 0)

        mycursor.execute(sql, val)

        mydb.commit()

    except:
        return

    try:
        sql = "INSERT INTO {papersread} (DOI, RelevanceRating) " \
              "VALUES (%s, %s)".format(papersread=papersread)
        val = (doi, 5)

        mycursor.execute(sql, val)

        mydb.commit()

    except:
        return


def findExistingUser(username):
    try:
        sql = "SELECT username FROM user " \
              "WHERE username = (%s)"
        val = username

        mycursor.execute(sql, (val,))

        result = mycursor.fetchall()

        print(result)

    except Exception as e:
        print(e)
        print("No user with that username.")


def changeUsers():
    print("MISSING CODE: changeUsers")


def addUser():
    newUsername = input("Please input a new username: ")
    interest1 = input("Please input first research interest: ")
    interest2 = input("Please input second research interest: ")
    interest3 = input("Please input third research interest: ")

    citationinfo = newUsername + '_citationinfo'
    citationcount = newUsername + '_citationcount'
    papersread = newUsername + '_papersread'

    sql = "INSERT INTO User (Username, Interest1, Interest2, Interest3) VALUES (%s, %s, %s, %s)"
    val = (newUsername, interest1, interest2, interest3)

    mycursor.execute(sql, val)

    mydb.commit()

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

    #sql = "CREATE TABLE IF NOT EXISTS {papersread} (" \
    #      "`DOI` VARCHAR(60) NOT NULL, " \
    #      "`RelevanceRating` INT NULL, " \
    #      "INDEX %s (`DOI` ASC) " \
    #      "PRIMARY KEY (`DOI`), " \
    #      "CONSTRAINT %s " \
    #      "FOREIGN KEY (`DOI`) " \
    #      "REFERENCES {citationinfo} (`DOI`) " \
    #      "ON DELETE CASCADE " \
    #      "ON UPDATE CASCADE)".format(papersread=papersread, citationinfo=citationinfo)

    #constraint = newUsername + '_fk_papers read_citation info1'
    #index = newUsername + '_fk_papers read_citation info1_idx'

    #val = (constraint, index)

    #mycursor.execute(sql, val)

    #index = newUsername + '_fk_citation = count_citation info_idx'
    #constraint = newUsername + '_fk_citation count_citation info'

    #sql = "CREATE TABLE IF NOT EXISTS {citationcount} (" \
    #      "`DOI` VARCHAR(60) NOT NULL, " \
    #      "`CitationCount` INT NULL, " \
    #      "INDEX {'index'} (`DOI` ASC)," \
    #      "PRIMARY KEY (`DOI`)," \
    #      "CONSTRAINT {'constraint'}" \
    #      "FOREIGN KEY (`DOI`)" \
    #      "REFERENCES {citationinfo} (`DOI`)" \
    #      "ON DELETE CASCADE " \
    #      "ON UPDATE CASCADE)".format(citationcount=citationcount, index=index, constraint=constraint, citationinfo=citationinfo)

    #val = (index, constraint)


def clearWeb():
    citationinfo = username + '_citationinfo'
    citationcount = username + '_citationcount'

    sql = "DELETE FROM {citationinfo} " \
          "WHERE levelnumber > -1".format(citationinfo=citationinfo)

    mycursor.execute(sql)
    mydb.commit()

    sql = "DELETE FROM {citationcount}".format(citationcount=citationcount)

    mycursor.execute(sql)
    mydb.commit()


def showRecommendedPapers():
    papersread = username + '_papersread'
    citationinfo = username + '_citationinfo'

    try:
        sql = "SELECT Interest1, Interest2, Interest3 " \
              "FROM User " \
              "WHERE Username = (%s)"

        val = (username, )

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

        for result in results:
            print(result)

    except Exception as e:
        print(e)






def showPapersInRange(year1, year2):
    citationinfo = 'citationinfo'

    try:
        sql = "SELECT DOI, Title, Year FROM {citationinfo} " \
              "WHERE Year >= (%s) AND Year <= (%s)" \
              "ORDER BY Year".format(citationinfo=citationinfo)

        val = (year1, year2)

        mycursor.execute(sql, val)

        results = mycursor.fetchall()

        for result in results:
            print(result)


    except Exception as e:
        print(e)


def showSharedPapers(username1, username2):
    citationinfo1 = username1 + '_citationinfo'
    citationinfo2 = username2 + '_citationinfo'

    try:
        sql = "SELECT t1.DOI, t1.Title " \
              "FROM {citationinfo1} as t1 " \
              "INNER JOIN {citationinfo2} as t2 " \
              "ON t1.DOI = t2.DOI".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

        mycursor.execute(sql)

        results = mycursor.fetchall()

        for result in results:
            print(result)

        sql = "SELECT COUNT(*) " \
              "FROM " \
              "(SELECT t1.DOI, t1.Title " \
              "FROM {citationinfo1} as t1 " \
              "INNER JOIN {citationinfo2} as t2 " \
              "ON t1.DOI = t2.DOI)" \
              "AS matched".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

        mycursor.execute(sql)

        result = mycursor.fetchall()

        print(result[0][0])

    except Exception as e:
        print(e)

def showAllPapers(username1, username2):
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

        for result in results:
            print(result)

        sql = "SELECT COUNT(*) " \
              "FROM " \
                "(SELECT DOI, Title " \
                "FROM {citationinfo1} " \
                "UNION DISTINCT " \
                "SELECT DOI, Title " \
                "FROM {citationinfo2})" \
                "AS total".format(citationinfo1=citationinfo1, citationinfo2=citationinfo2)

        mycursor.execute(sql)

        result = mycursor.fetchall()

        print(result[0][0])

    except Exception as e:
        print(e)


#rawCitation, tag = navToDOI('10.1038/nchembio.2217')
#parseCitationIntoArray(rawCitation)

#navToDOI('10.1021~2Fcb6003756')

#DOI for demo:
#doi:10.1038/nchembio.2217

#chrome_options = Options()
#chrome_options.add_argument("--headless")
#chrome_options.add_argument("--window-size=1920x1080")
#options=chrome_options

driver = webdriver.Chrome()

mydb = mysql.connector.connect(
    host="localhost",
    user="RWalderbach",
    password="SQLPassword19",
    database="demodatabase"
)

mycursor = mydb.cursor()

#mycursor.execute("DELETE FROM citationinfo")
#mycursor.execute("DELETE FROM citationcount")

#rawCitation, tag = navToDOI('10.1038/nchembio.2217')
#doi, author, title, journal, year = parseCitationIntoArray(rawCitation)
#
#sql = "INSERT INTO citationinfo (LevelNumber, DOI, Authors, Title, Journal, Year, HasButton, Visited) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
#val = (0, doi, author, title, journal, year, 1, 0)
#
#mycursor.execute(sql, val)
#
#mydb.commit()

#navToCitations('10.1038/nchembio.2217', 1)

#

#addUser()

#addPaperToStart('10.1111/febs.14185')
iterativeCitationFind()

#findExistingUser(input("Enter a username: "))

#showPapersInRange(2000, 2010)

#showSharedPapers('rwalderbach', 'hhassan')

#showRecommendedPapers()