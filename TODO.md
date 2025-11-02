# TODO

Create the pages below in order to complete the website. When complete, mark the page as complete, changing an [ ] to an [x].
Since the frontend is being built before the backend, use dummy API calls to simulate the backend functionality, and accept all passwords and invite codes as valid.

## Frontend
- The frontend will be built with React. The website will have a dark theme.

[x] Password entry page

  - This is the main page of the website, seen by returning users or users who have already accepted an invite, or people who have not accepted an invite yet.
  - This should be a simple page with a form that has a password entry field, nothing else (no buttons, no links, no text, nothing else.) The entry field should be centered in the page. The password in the entry field will be hidden and displayed as asterisks. No password reveal button.
  - Once the password is submitted, a request will be made to the backend to validate the password. This process will take 2 seconds to complete (on the backend, a timer will be started and the request will be blocked for 2 seconds.) so that the user cannot submit the password too quickly.
  - When the password is submitted the page will display a simple countdown timer of 2 seconds. If the password is valid, the user will be redirected to the next page. If the password is invalid, the input field will be cleared and highlighted in red.
  - If the password is valid, the user will be redirected to the website.
  

[ ] Invite acceptance page
  
  - This page is seen by users who have been linked an invite to the website by someone who is already has a password and access to the website. This page is used to accept the invite and gain access to the website.
  - The page will display the password alongside instructions to write it down, and never link the actual host website, but generate an invite code using the invite generation widget on the host website.

[ ] Admin panel

  - This will only be accessible through localhost:3000/admin.
  - The panel will display a list of all the passwords created and invites generated.
  - It will have a button to generate a new invite or password.
  - You will also be able to revoke an invite or password from here.
  - You will also be able to edit an invite (change the password it is linked to, change the number of uses it has, etc.)

## Backend

The backend will be built with Python, FastAPI, and SQLite. Make sure you are using the latest stable version of FastAPI and SQLite. Create a new virtual environment for the backend and install the dependencies.

[x] Database creation
  - The database will be an sqlite database called tree.db in backend/db/tree.db. Use WAL mode for the database.
  - The Python code will create the database and the tables if they do not exist.
  - The database will use a single table to represent both passwords and invites as nodes in a hierarchical tree structure:
    - nodes table:
      - id: INTEGER PRIMARY KEY AUTOINCREMENT
      - node_type: TEXT NOT NULL CHECK (node_type IN ('password', 'invite'))
      - value: TEXT NOT NULL (stores either password or invite code)
      - redirect_url: TEXT NOT NULL (URL to redirect to when password/invite is used)
      - parent_id: INTEGER (NULL for root passwords, references parent node for invites)
      - uses: INTEGER DEFAULT 0
      - max_uses: INTEGER (optional: limit how many times this can be used)
      - is_active: BOOLEAN DEFAULT TRUE
      - expires_at: DATETIME (optional: when this node expires and becomes invalid)
      - created_at: DATETIME DEFAULT CURRENT_TIMESTAMP
      - updated_at: DATETIME DEFAULT CURRENT_TIMESTAMP
      - FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
    - Indexes:
      - CREATE INDEX idx_parent_id ON nodes(parent_id)
      - CREATE INDEX idx_node_type ON nodes(node_type)

[x] Password validation
  - This will be a simple API endpoint that will validate a password and return the redirect URL to the next page.
  - The endpoint will be /api/validate-password and will accept a POST request with a password in the body.
  - The backend will read from the sqlite database, looking for a node with the value of the password and node_type of 'password'.
  - If the node is found and is active (and not expired), the endpoint will return a JSON object with the redirect URL from the database.
  - If the node is not found, the endpoint will return a 403 Forbidden response.

## Future functionality

  [ ] Network graph
    - Add a network graph page to both the admin panel and the invite acceptance page. 
    - This graph will show the relationships between the invites and passwords. (All invites generated under a password will be shown as children of that password, and if someone generates an invite, it will be shown as a child of the invite that generated it. These invites nodes will show as smaller than the password node at the top of the tree.)
    - On the invite acceptance page, the graph will be showed beside the password, with the node the user is currently on highlighted. This won't be the exact same as the admin panel graph since it will be view only and not editable.
    - On the admin panel, the graph will be shown on the "Graph" page.
    - At the top of a tree, the root node will be the password that was used to generate the invite. There can be multiple passwords for website access, so multiple root nodes may be shown.
