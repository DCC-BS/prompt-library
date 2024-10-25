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
         upvotes INTEGER DEFAULT 0)
    ''')
    conn.commit()
    conn.close()

def save_prompt(prompt: Prompt) -> int:
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO prompts (name, author, template, example_values, upvotes)
        VALUES (?, ?, ?, ?, ?)
    ''', (prompt.name, prompt.author, prompt.template, prompt.example_values, prompt.upvotes))
    prompt_id = c.lastrowid
    conn.commit()
    conn.close()
    return prompt_id

def update_prompt(prompt: Prompt):
    conn = sqlite3.connect('prompts.db')
    c = conn.cursor()
    c.execute('''
        UPDATE prompts
        SET name=?, author=?, template=?, example_values=?, upvotes=?
        WHERE id=?
    ''', (prompt.name, prompt.author, prompt.template, prompt.example_values, prompt.upvotes, prompt.id))
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