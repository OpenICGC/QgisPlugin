# encoding: utf-8
"""
*******************************************************************************
Module with functions for sending emails in Windows environments using Outlook
*******************************************************************************
"""

import win32com
import win32com.client


class eMail(object):
    def __init__(self, to, cc, subject, htmlbody, attachment_files = []):
        """ Object initialization with all email requireds parameters """

        # If we do not pass the HTML header we have it
        if htmlbody.upper().find("<BODY>") < 0:
            htmlbody = """
                <HTML>
                    <HEAD></HEAD>
                    <BODY>
                        %s
                    </BODY>
                </HTML>
                """ % htmlbody

        # We create an Outlook email object and fill it out
        obj = win32com.client.Dispatch("Outlook.Application")
        olMailItem = 0x0
        self.newMail = obj.CreateItem(olMailItem)
        self.newMail.To = to
        self.newMail.CC = cc
        self.newMail.Subject = subject
        for attachment in attachment_files:
            self.newMail.Attachments.Add(attachment)
        self.newMail.HTMLBody = htmlbody

    def send(self):
        # send email
        self.newMail.Send()

    def open(self):
        # open a new mail and give it focus
        inspector = self.newMail.getinspector
        inspector.Activate()
