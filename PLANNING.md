Architecture:
  Frontend:
    - React
    - Tailwind
    - Next.js
  Backend:
    - FastAPI
  Database:
    - PostgreSQL

Pages:

- Home page (password entry)
- Admin panel
- Invite accept page

## Visitor flow

Visiting the gateway will only show a password entry page. If the password is correct, the user will be redirect to the website the gateway is protecting. This will also grant the user a token that can be used to access the website for a set amount of time.

Visiting a gateway with at an invite link will redirect a user to an invite accept page. This page will show the user a password and a button to accept the invite. The user is intended to write down the password and then use it to access the website when the token expires, or share it to others (though hitting the share button is preferred). After hitting the accept button, the user will be redirected to the website the gateway is protecting. The user will also be instructed NOT to share the host website, only link to the gateway.

Once the user is on the host website, the host website can show a widget that will show a share button that will generate a unique invite link to the gateway that uses the same password as the user's. This way, the user can link directly to certain pages on the host website instead of just sharing the link to the gateway and their password. In addition, this invite link will go directly to the invite accept page, rather than the password entry page. So the user will get logged in immediately and granted a bearer token.

## Admin flow

The admin panel can only be accessed through localhost. The admin panel will keep track of all invite links and passwords, how many times they've been used, and ...

## Backend functionality

Rather than DDNS, the host site will hit an API endpoint to update it's own IP address record for redirection. This way, the host can change its IP address regularly.

## Host setup

The host should be able to setup a cron job to hit an API endpoint to update it's own IP address record for redirection. This way, the host can change its IP address regularly.

As for authentication, the host should be set up to only allow access if a bearer token is provided. This bearer token should be checked with the gateway. This way, the host can only be accessed by the gateway.

The host will also implement a widget that will show a share button that will hit the gateway API to generate a unique invite link to that part of the host website.

## Admin panel

The admin panel allows the user to manage invites, passwords, and see a network graph of all invite links and passwords. It also shows usages for both and allows the user to revoke, edit, and create new invite links and passwords.

When revoking access to an invite, this will make the password that is associated with that invite no longer work. (As well as any outstanding invite links generated within that tree.) This way, all the invites that were created within that tree no longer work, including the parent at the very top.