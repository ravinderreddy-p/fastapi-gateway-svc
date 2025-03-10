import uuid
import time
# Simple in-memory session store (REPLACE WITH DATABASE IN PRODUCTION)
sessions = {}

class SessionManager:
    def create_session(self, access_token, refresh_token):
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"access_token": access_token, "refresh_token": refresh_token}
        return session_id

    def get_session(self, session_id):
        return sessions.get(session_id)

    def delete_session(self, session_id):
        if session_id in sessions:
            del sessions[session_id]


session_manager = SessionManager()  # Create an instance of the session manager
