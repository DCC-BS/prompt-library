import sqlite3
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Prompt:
    id: Optional[int]
    name: str
    author: str
    template: str
    example_values: str
    upvotes: int
    version: int = 1
    parent_id: Optional[int] = None
    created_at: Optional[str] = None

def init_db():
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prompts
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         name TEXT NOT NULL,
         author TEXT NOT NULL,
         template TEXT NOT NULL,
         example_values TEXT NOT NULL,
         upvotes INTEGER DEFAULT 0,
         version INTEGER NOT NULL,
         parent_id INTEGER,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         FOREIGN KEY (parent_id) REFERENCES prompts (id))
    ''')
    conn.commit()
    conn.close()

def save_prompt(prompt: Prompt) -> int:
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO prompts (name, author, template, example_values, upvotes, version, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (prompt.name, prompt.author, prompt.template, prompt.example_values, prompt.upvotes, prompt.version, prompt.parent_id))
    prompt_id = c.lastrowid
    conn.commit()
    conn.close()
    return prompt_id

def update_prompt(prompt: Prompt):
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    
    # Get the latest version for this prompt
    c.execute('''
        SELECT MAX(version)
        FROM prompts
        WHERE id = ? OR parent_id = ?
    ''', (prompt.id, prompt.id))
    
    latest_version = c.fetchone()[0] or 1
    
    # Insert new version
    c.execute('''
        INSERT INTO prompts (name, author, template, example_values, upvotes, version, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (prompt.name, prompt.author, prompt.template, prompt.example_values, 
          0, latest_version + 1, prompt.id))
    
    conn.commit()
    conn.close()

def get_all_prompts() -> List[Prompt]:
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('SELECT * FROM prompts')
    prompts = [Prompt(*row) for row in c.fetchall()]
    conn.close()
    return prompts

def upvote_prompt(prompt_id: int):
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('UPDATE prompts SET upvotes = upvotes + 1 WHERE id = ?', (prompt_id,))
    conn.commit()
    conn.close()

def delete_prompt(prompt_id: int):
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('DELETE FROM prompts WHERE id = ?', (prompt_id,))
    conn.commit()
    conn.close()

def get_prompt_versions(prompt_id: int) -> List[Prompt]:
    """Get all versions of a prompt, ordered by version number descending."""
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('''
        SELECT *
        FROM prompts 
        WHERE id = ? OR parent_id = ? OR id IN (
            SELECT parent_id FROM prompts WHERE id = ? OR parent_id = ?
        )
        ORDER BY version DESC
    ''', (prompt_id, prompt_id, prompt_id, prompt_id))
    prompts = [Prompt(*row) for row in c.fetchall()]
    conn.close()
    return prompts

def get_latest_versions() -> List[Prompt]:
    """Get the latest version of each prompt family."""
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('''
        WITH RankedPrompts AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY COALESCE(parent_id, id)
                       ORDER BY version DESC
                   ) as rn
            FROM prompts
        )
        SELECT id, name, author, template, example_values, upvotes, version, parent_id, created_at
        FROM RankedPrompts
        WHERE rn = 1
        ORDER BY upvotes DESC
    ''')
    prompts = [Prompt(*row) for row in c.fetchall()]
    conn.close()
    return prompts

