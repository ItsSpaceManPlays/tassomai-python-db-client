used_errcodes = {}

class DuplicateCodeEntry(Exception):
    def __init__(self, message):
        super().__init__(message)

class ErrCode():
    def __init__(self, code_int: int, code_message: str, short_name: str):
        if code_int in used_errcodes:
            other_code = used_errcodes[code_int]
            raise DuplicateCodeEntry(f"Code {code_int} already exists as {other_code.shortname}")
        used_errcodes[code_int] = self

        self.code = code_int
        self.message = code_message
        self.shortname = short_name

    def __str__(self):
        return self.message
    
    def __int__(self):
        return self.code

class ERROR_CODES:
    DB_DUPEKEY = ErrCode(0, "Database already contains that key", "DB_DUPEKEY")
    DB_WRITEEXCEPTION = ErrCode(1, "Write to database failed", "DB_WRITEEXCEPTION")
    DB_WRITESUCCESS = ErrCode(2, "Database write succeeded", "DB_WRITESUCCESS")
    AUTH_WRONGTOKEN = ErrCode(10, "Wrong authentication code provided to question write request", "AUTH_WRONGTOKEN")