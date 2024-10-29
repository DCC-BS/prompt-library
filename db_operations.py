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

    def __eq__(self, other):
        if not isinstance(other, Prompt):
            return False

        # Compare all fields except id (since it might be None for new prompts)
        # and upvotes (since they might change independently)
        return (
            self.name == other.name
            and self.author == other.author
            and self.template == other.template
            and self.example_values == other.example_values
            and self.version == other.version
            and self.parent_id == other.parent_id
        )


@dataclass
class TestCase:
    id: Optional[int]
    prompt_id: int
    input_values: str
    expected_output: str
    created_at: Optional[str] = None

    def __eq__(self, other):
        if not isinstance(other, TestCase):
            return False

        # Compare all fields except id (since it might be None for new test cases)
        # and created_at (since it's system-generated)
        return (
            self.prompt_id == other.prompt_id
            and self.input_values == other.input_values
            and self.expected_output == other.expected_output
        )


def init_db():
    conn = sqlite3.connect("prompts.db")
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute("""
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
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS test_cases
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         prompt_id INTEGER NOT NULL,
         input_values TEXT NOT NULL,
         expected_output TEXT NOT NULL,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         FOREIGN KEY (prompt_id) REFERENCES prompts (id) ON DELETE CASCADE)
    """)

    conn.commit()
    conn.close()


def save_prompt(prompt: Prompt) -> int:
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO prompts (name, author, template, example_values, upvotes, version, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            prompt.name,
            prompt.author,
            prompt.template,
            prompt.example_values,
            prompt.upvotes,
            prompt.version,
            prompt.parent_id,
        ),
    )
    prompt_id = c.lastrowid
    conn.commit()
    conn.close()
    return prompt_id


def update_prompt(prompt: Prompt) -> int:
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()

    # Get the latest version for this prompt
    c.execute(
        """
        SELECT MAX(version)
        FROM prompts
        WHERE id = ?
        """,
        (prompt.parent_id,),
    )
    latest_version = c.fetchone()[0] or 1

    # Insert new version
    c.execute(
        """
        INSERT INTO prompts (name, author, template, example_values, upvotes, version, parent_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            prompt.name,
            prompt.author,
            prompt.template,
            prompt.example_values,
            prompt.upvotes,
            latest_version + 1,
            prompt.parent_id,
        ),
    )
    
    prompt_id = c.lastrowid

    conn.commit()
    conn.close()
    return prompt_id


def get_all_prompts() -> List[Prompt]:
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute("SELECT * FROM prompts")
    prompts = [Prompt(*row) for row in c.fetchall()]
    conn.close()
    return prompts


def upvote_prompt(prompt_id: int):
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute("UPDATE prompts SET upvotes = upvotes + 1 WHERE id = ?", (prompt_id,))
    conn.commit()
    conn.close()


def delete_prompt(prompt_id: int):
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    conn.commit()
    conn.close()


def get_prompt_versions(prompt_id: int) -> List[Prompt]:
    """Get all versions of a prompt, ordered by version number descending."""
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT *
        FROM prompts 
        WHERE id = ? OR parent_id = ? OR id IN (
            SELECT parent_id FROM prompts WHERE id = ? OR parent_id = ?
        )
        ORDER BY version DESC
    """,
        (prompt_id, prompt_id, prompt_id, prompt_id),
    )
    prompts = [Prompt(*row) for row in c.fetchall()]
    conn.close()
    return prompts


def get_latest_versions() -> List[Prompt]:
    """Get the latest version of each prompt family."""
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute("""
        WITH RECURSIVE PromptHierarchy AS (
        -- Anchor: Get all prompts without parents (root prompts)
        SELECT 
            id,
            id as root_id,
            version,
            parent_id,
            1 as level
        FROM prompts
        WHERE parent_id IS NULL

        UNION ALL

        -- Recursive part: Get all children and their relationship to root
        SELECT 
            p.id,
            ph.root_id,
            p.version,
            p.parent_id,
            ph.level + 1
        FROM prompts p
        JOIN PromptHierarchy ph ON p.parent_id = ph.id
    ),
    LatestVersions AS (
        SELECT p.*,
            ROW_NUMBER() OVER (
                PARTITION BY ph.root_id
                ORDER BY ph.level DESC, p.version DESC
            ) as rn
        FROM prompts p
        LEFT JOIN PromptHierarchy ph ON p.id = ph.id
    )
    SELECT id, name, author, template, example_values, upvotes, version, parent_id, created_at
    FROM LatestVersions
    WHERE rn = 1
    ORDER BY upvotes DESC;
    """)
    prompts = [Prompt(*row) for row in c.fetchall()]
    conn.close()
    return prompts


def save_test_case(test_case: TestCase) -> int:
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO test_cases (prompt_id, input_values, expected_output)
        VALUES (?, ?, ?)
    """,
        (test_case.prompt_id, test_case.input_values, test_case.expected_output),
    )
    test_case_id = c.lastrowid
    conn.commit()
    conn.close()
    return test_case_id


def get_test_cases(prompt_parent_id: int) -> List[TestCase]:
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute("SELECT * FROM test_cases WHERE prompt_id = ?", (prompt_parent_id,))
    test_cases = [TestCase(*row) for row in c.fetchall()]
    conn.close()
    return test_cases


def delete_test_case(test_case_id: int):
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute("DELETE FROM test_cases WHERE id = ?", (test_case_id,))
    conn.commit()
    conn.close()


def update_test_case(test_case: TestCase):
    conn = sqlite3.connect("prompts.db")
    c = conn.cursor()
    c.execute(
        """
        UPDATE test_cases
        SET input_values = ?,
            expected_output = ?
        WHERE id = ?
    """,
        (test_case.input_values, test_case.expected_output, test_case.id),
    )
    conn.commit()
    conn.close()
