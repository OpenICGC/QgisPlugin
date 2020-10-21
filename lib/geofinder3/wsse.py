"""
*******************************************************************************
Module that allows you to add SOAP packets with password coded in MD5 / BASE64
Downloaded code:
    https://gist.github.com/copitux/5029872

Changes tagged with "## Python3 change:"
*******************************************************************************
"""

from base64 import b64encode
from suds.wsse import UsernameToken, Token
try:
    from hashlib import sha1, md5
except:
    from sha import new as sha1, md5


class UsernameDigestToken(UsernameToken):
    """
    Represents a basic I{UsernameToken} WS-Security token with password digest
    @ivar username: A username.
    @type username: str
    @ivar password: A password.
    @type password: str
    @ivar nonce: A set of bytes to prevent reply attacks.
    @type nonce: str
    @ivar created: The token created.
    @type created: L{datetime}

    @doc: http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0.pdf
    """

    def __init__(self, username=None, password=None):
        UsernameToken.__init__(self, username, password)
        self.setcreated()
        self.setnonce()

    def setnonce(self, text=None):
        """
        Set I{nonce} which is arbitraty set of bytes to prevent
        reply attacks.
        @param text: The nonce text value.
            Generated when I{None}.
        @type text: str

        @override: Nonce save binary string to build digest password
        """
        if text is None:
            s = []
            s.append(self.username)
            s.append(self.password)
            s.append(Token.sysdate())
            m = md5()
            m.update(':'.join(s).encode('ascii')) ## Python3 change: We we need to encode the value
            self.raw_nonce = m.digest()
            self.nonce = b64encode(self.raw_nonce).decode('ascii') ## Python3 change: We we need to encode the value
        else:
            self.nonce = text

    def xml(self):
        usernametoken = UsernameToken.xml(self)
        password = usernametoken.getChild('Password')
        nonce = usernametoken.getChild('Nonce')
        created = usernametoken.getChild('Created')

        password.set('Type', 'http://docs.oasis-open.org/wss/2004/01/'
                             'oasis-200401-wss-username-token-profile-1.0'
                             '#PasswordDigest')
        s = sha1()
        s.update(self.raw_nonce)
        s.update(created.getText().encode('ascii')) ## Python3 change: We we need to encode the value
        s.update(password.getText().encode('ascii')) ## Python3 change: We we need to encode the value
        password.setText(b64encode(s.digest()).decode('ascii')) ## Python3 change: We we need to encode the value

        nonce.set('EncodingType', 'http://docs.oasis-open.org/wss/2004'
            '/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary')
        
        return usernametoken
