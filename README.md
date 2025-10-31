# Background & overview

Cascading Trust is a gateway service that allows people to share and spread their links and websites "under the radar" by operating under the protection of this gateway rather than linking viewers directly to their website (which could result in a subpoena, compromise, etc). This is accompanied with  features that allow for control over the access and spread of content.

I created this to allow people who fear prosecution from corrupt forces and those who wish to evade surveillance a way to share easily spread content without being subpoenaed, tracked, and prosecuted. The system was made with journalists and whistleblowers in mind, but can be used by anyone who wishes to share while remaining under the radar or even just people who want better access control over their content, and the spread of their content. I aim for this to be some type of "in between" for those who are not under extreme survailence but still have secrets they wish to share.

While this is absolutely not a silver bullet for hosting privacy, it enables sharing in a way that is far easier to access for the average person than more secure alternatives (TOR & IPFS), while still providing a greater level of privacy and security than regular open internet hosting.

## WARNING

Under the radar is NOT invisible. This system is imperfect. If you are the target of a government or other entity with enough resources, it is possible they will be able to identify your end host, and in turn, maybe even your content, and you.

Here are some ways it could model be broken (ignoring host compromise, that's on you):

- Subpoenas to a user's (or host's) ISP that were able to identify the redirect from the gateway to the end host
- A user with invite permissions inviting a compromised user to join the trust
- The gateway being compromised

You absolutely *can*, but probably *shouldn't* trust me to be a good steward of the cascading trust gateway that I host. I do not monitor the activities of the gateway but if you are truly concerned about your website being accessed by those outside your trusted network, you should probably clone this repository and run your own gateway on your own secured server. Also, please do not host illegal content on my gateway. (you should absolutely never break the law!)

## Architecture

```
                                                       ┌────┐
                ┌───────────────────────────────────── │DDNS│
                │                                      └────┘
                │                                         ▲
                │                                         │
                ▼                                         │
          1984.is (Iceland)                         Host server
        ┌────────────────────┐                    ┌──────────────┐
        │ cascadingtrust.net │                    │              │   ┌──────────┐
User───►│     (gateway)      ├──User (w/ token)──►│ Host website ◄───┤ external │
        │   Password/token   │                    │              │   └──────────┘
        └────────────────────┘                    └──────────────┘
```

## Security

Obviously one of the key aspects of sharing is the gateway invite link, therefore it's extremely important to prevent someone from guessing invite links. This is done by agressive rate limiting and blocking of suspicious activity. Additionally, the gateway has a number of honeypot invite links that instantly block and report hits to them.
