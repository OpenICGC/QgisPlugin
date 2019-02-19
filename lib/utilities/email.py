# encoding: utf-8
"""
MODULE: email.py

Funcions per enviar emails

"""
import win32com
import win32com.client


class eMail(object):
    def __init__(self, to, cc, subject, htmlbody, attachment_files = []):
        # Si no es passen la capçalera HTML la possem nosaltres
        if htmlbody.upper().find("<BODY>") < 0:
            htmlbody = """
                <HTML>
                    <HEAD></HEAD>
                    <BODY>
                        %s
                    </BODY>
                </HTML>
                """ % htmlbody

        # Creem un objecte email de l'Outlook i l'omplim
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
        self.newMail.Send()

    def open(self):
        # open a new mail and give it focus
        inspector = self.newMail.getinspector
        inspector.Activate()
