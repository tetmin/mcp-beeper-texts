# Beeper Texts Database Schema Analysis (Detailed)

This document provides a detailed analysis of the key tables in the Beeper Texts databases, including `account.db`, `index.db`, and the platform-specific `megabridge.db` files.

---

## `index.db` - UI and Application State

### `mx_room_messages`

**Purpose**: This is the primary table for the application's UI, containing an optimized and decorated index of all messages from all platforms. It is designed for fast rendering of the chat history.

| Column                  | Type    | NOT NULL | Default | Description                                                                                             |
| ----------------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `id`                    | INTEGER | ✅        |         | **Primary Key**. A unique auto-incrementing integer for each row.                                       |
| `roomID`                | TEXT    | ✅        |         | The Matrix Room ID (e.g., `!gM1Gud...:local-whatsapp.localhost`). **Foreign Key** to `threads.threadID`. |
| `eventID`               | TEXT    | ✅        |         | The Matrix Event ID (e.g., `$ls1eA7...`). **Unique**.                                                    |
| `senderContactID`       | TEXT    | ✅        |         | The Matrix User ID of the sender (e.g., `@o5owAv...:local-whatsapp.localhost`).                          |
| `timestamp`             | INTEGER | ✅        |         | Unix timestamp (nanoseconds) of the message.                                                            |
| `isEdited`              | INTEGER | ✅        | 0       | Boolean (0/1) indicating if the message has been edited.                                                |
| `lastEditionID`         | TEXT    |          |         | The `eventID` of the last edit event.                                                                   |
| `isDetached`            | INTEGER | ✅        | 0       | Boolean (0/1) indicating if the message is detached from the main timeline.                             |
| `lastEditionTimestamp`  | INTEGER |          |         | Unix timestamp (nanoseconds) of the last edit.                                                          |
| `lastEditionOrder`      | INTEGER |          |         | The `hsOrder` of the last edit.                                                                         |
| `isDeleted`             | INTEGER | ✅        | 0       | Boolean (0/1) indicating if the message has been deleted.                                               |
| `isEncrypted`           | INTEGER | ✅        | 0       | Boolean (0/1) indicating if the message is encrypted.                                                   |
| `inReplyToID`           | TEXT    |          |         | The `eventID` of the message being replied to.                                                          |
| `isReplyThreadFallback` | INTEGER |          |         | Boolean (0/1) indicating if this is a fallback for a reply thread.                                      |
| `type`                  | TEXT    | ✅        |         | The message type (e.g., `TEXT`, `HIDDEN`, `IMAGE`).                                                     |
| `hsOrder`               | INTEGER | ✅        |         | A homeserver-assigned order for messages within a room.                                                 |
| `isSentByMe`            | INTEGER | ✅        |         | Boolean (0/1) indicating if the message was sent by the current user.                                   |
| `replyThreadID`         | TEXT    |          |         | The ID of the reply thread.                                                                             |
| `replyCount`            | INTEGER |          |         | The number of replies to this message.                                                                  |
| `replyThreadRootID`     | TEXT    |          |         | The `eventID` of the root message in a reply thread.                                                    |
| `protocol`              | TEXT    |          |         | The protocol the message originated from (e.g., `whatsapp`, `telegram`).                                |
| `shouldNotify`          | INTEGER |          |         | Boolean (0/1) indicating if a notification should be shown for this message.                            |
| `shouldPreview`         | INTEGER |          |         | Boolean (0/1) indicating if a preview should be shown for this message.                                 |
| `countsAsUnread`        | INTEGER |          |         | Boolean (0/1) indicating if this message contributes to the unread count.                               |
| `lastDeletionID`        | TEXT    |          |         | The `eventID` of the deletion event.                                                                    |
| `editedType`            | TEXT    |          |         | The type of the message after being edited.                                                             |
| `mentions`              | TEXT    |          |         | JSON array of user IDs mentioned in the message.                                                        |
| `message`               | JSON    | ✅        |         | A rich JSON object containing the full message content and metadata. Includes `text` (message body), `attachments`, `links`, `mentions`, `extra` metadata, and more. **This contains searchable message content.** |
| `sendStatus`            | JSON    |          |         | JSON object representing the sending status of the message.                                             |
| `text_content`          | TEXT    |          |         | The plain text content of the message.                                                                  |
| `text_formattedContent` | TEXT    |          |         | The formatted (HTML) content of the message.                                                            |
| `text_format`           | TEXT    |          |         | The format of the `text_formattedContent` (e.g., `org.matrix.custom.html`).                             |
| `echo_echoID`           | VARCHAR |          |         | ID for optimistic local message echoes.                                                                 |
| `echo_state`            | VARCHAR |          |         | State of the local echo (e.g., `sending`, `sent`, `failed`).                                            |
| `echo_canAutoRetry`     | INTEGER |          | 0       | Boolean (0/1) indicating if a failed message can be automatically retried.                              |
| `echo_isRetryScheduled` | INTEGER |          | 0       | Boolean (0/1) indicating if a retry is scheduled.                                                       |
| `echo_retryCount`       | INTEGER |          | 0       | The number of times a message send has been retried.                                                    |
| `echo_errorCode`        | INTEGER |          |         | The error code if the message failed to send.                                                           |
| `echo_errorMessage`     | VARCHAR |          |         | The error message if the message failed to send.                                                        |
| `echo_groupID`          | VARCHAR |          |         | The group ID for a batch of messages.                                                                   |
| `echo_groupIndex`       | INTEGER |          |         | The index of the message within a group.                                                                |

**Relationships**:
- `roomID` -> `threads.threadID`
- `senderContactID` -> `ghost.id` (implicitly, via Matrix User ID)
- `inReplyToID` -> `mx_room_messages.eventID`

### `threads`

**Purpose**: This table holds information about each conversation thread, including its participants, title, and other metadata.

| Column      | Type    | NOT NULL | Default | Description                                                                                             |
| ----------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `threadID`  | VARCHAR | ✅        |         | **Primary Key**. The Matrix Room ID for the thread.                                                     |
| `accountID` | VARCHAR |          |         | The account ID this thread belongs to.                                                                  |
| `thread`    | JSON    | ✅        |         | A rich JSON object containing detailed thread metadata including `participants`, `title`, `extra.tags`, archive/priority flags, AND `partialLastMessage` with the full text of the last message. **Contains searchable last message content.** |
| `timestamp` | INTEGER |          | 0       | The timestamp of the last activity in the thread.                                                       |

**Relationships**:
- `threadID` -> `mx_room_messages.roomID`

### `thread_props`

**Purpose**: Stores properties related to threads, including draft messages.

| Column      | Type    | NOT NULL | Default | Description                                                                                             |
| ----------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `accountID` | VARCHAR |          |         | The account ID this thread property belongs to. Can be NULL for global properties.                      |
| `threadID`  | VARCHAR | ✅        |         | **Primary Key (with accountID)**. The Matrix Room ID for the thread. **Foreign Key** to `threads.threadID`. |
| `props`     | JSON    | ✅        |         | A JSON object containing various properties, such as `draftText` for message drafts.                    |

**Relationships**:
- `threadID` -> `threads.threadID`

### `breadcrumbs`

**Purpose**: Tracks user interaction with chats, such as open counts and last open times.

| Column         | Type    | NOT NULL | Default | Description                                                                                             |
| -------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `id`           | TEXT    | ✅        |         | **Primary Key**. The Matrix Room ID. **Foreign Key** to `threads.threadID`.                           |
| `openCount`    | INTEGER | ✅        | 0       | The number of times the chat has been opened.                                                           |
| `sentCount`    | INTEGER | ✅        | 0       | The number of messages sent in this chat.                                                               |
| `sentLast`     | INTEGER | ✅        | 0       | Timestamp of the last message sent in this chat.                                                        |
| `lastOpenTime` | INTEGER | ✅        | 0       | Timestamp of the last time the chat was opened.                                                         |

**Relationships**:
- `id` -> `threads.threadID`

### `mx_read_receipts`

**Purpose**: Stores read receipt information for messages.

| Column          | Type    | NOT NULL | Default | Description                                                                                             |
| --------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `roomID`        | VARCHAR | ✅        |         | **Primary Key (with userID)**. The Matrix Room ID. **Foreign Key** to `threads.threadID`.             |
| `userID`        | VARCHAR | ✅        |         | **Primary Key (with roomID)**. The Matrix User ID who sent the read receipt.                          |
| `relatesToID`   | VARCHAR | ✅        |         | The `eventID` of the message that this read receipt relates to. **Foreign Key** to `mx_room_messages.eventID`. |
| `hsOrder`       | INTEGER |          |         | The homeserver order of the event.                                                                      |
| `timestamp`     | INTEGER | ✅        |         | The timestamp of the read receipt.                                                                      |
| `lastVisibleEventID` | VARCHAR | ✅        | ''      | The last visible event ID.                                                                              |
| `hsSuborder`    | INTEGER |          |         | The homeserver suborder of the event.                                                                   |
| `hsOrderString` | VARCHAR |          |         | The homeserver order string.                                                                            |

**Relationships**:
- `roomID` -> `threads.threadID`
- `relatesToID` -> `mx_room_messages.eventID`

### `users`

**Purpose**: A central table for user information, though often empty as contacts are resolved per platform.

| Column      | Type    | NOT NULL | Default | Description                                                                                             |
| ----------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `userID`    | VARCHAR | ✅        |         | **Primary Key (with accountID)**. The Matrix User ID.                                                   |
| `accountID` | VARCHAR |          |         | The account ID this user belongs to. Can be NULL for global users.                                      |
| `user`      | JSON    | ✅        |         | A JSON object containing user details (e.g., display name, avatar URL).                                 |

**Relationships**:
- None explicitly defined in schema, but `userID` can relate to `senderContactID` in `mx_room_messages`.

### `accounts`

**Purpose**: Stores information about the different accounts connected to Beeper, including platform details and session information.

| Column       | Type    | NOT NULL | Default | Description                                                                                             |
| ------------ | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `accountID`  | VARCHAR | ✅        |         | **Primary Key**. Unique identifier for the account.                                                     |
| `platformName` | VARCHAR | ✅        |         | The name of the platform (e.g., `whatsapp`, `telegram`, `linkedin`).                                    |
| `state`      | VARCHAR | ✅        |         | The current state of the account (e.g., `connected`, `disconnected`, `error`).                          |
| `user`       | JSON    |          |         | JSON object containing user-specific information for this account.                                      |
| `session`    | JSON    |          |         | JSON object containing session-specific information for this account.                                   |
| `props`      | JSON    |          |         | JSON object for additional properties related to the account.                                           |

**Relationships**:
- `accountID` -> `threads.accountID`

---

## `account.db` - Matrix Protocol & Unified Message Events

### `local_events`

**Purpose**: Stores all raw Matrix protocol events, forming the core of the unified message system.

| Column            | Type    | NOT NULL | Default | Description                                                                                             |
| ----------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `room_id`         | TEXT    | ✅        |         | The Matrix Room ID.                                                                                     |
| `event_id`        | TEXT    | ✅        |         | **Primary Key**. The unique Matrix Event ID.                                                            |
| `sender`          | TEXT    | ✅        |         | The Matrix User ID of the event sender.                                                                 |
| `type`            | TEXT    | ✅        |         | The type of Matrix event (e.g., `m.room.message`, `m.room.member`, `m.room.create`).                    |
| `state_key`       | TEXT    |          |         | For state events, this identifies the specific state being set.                                         |
| `content`         | BLOB    |          |         | The raw JSON content of the Matrix event. This contains the actual message body, membership details, etc. |
| `redacts`         | TEXT    |          |         | The `event_id` of the event this event redacts (e.g., for message deletions).                           |
| `unsigned`        | BLOB    |          |         | Unsigned data associated with the event.                                                                |
| `stream_order`    | INTEGER | ✅        | 0       | An ordering value for events within the stream.                                                         |
| `stream_suborder` | INTEGER | ✅        | 0       | A sub-ordering value for events within the stream.                                                      |
| `event_ts`        | INTEGER | ✅        |         | The timestamp when the event occurred (from the homeserver).                                            |
| `created_ts`      | INTEGER | ✅        |         | The timestamp when the event was created locally.                                                       |
| `backed_up_ts`    | INTEGER |          |         | Timestamp when the event was backed up.                                                                 |
| `backup_backoff_ts` | INTEGER |          |         | Timestamp for backup retry backoff.                                                                     |

**Relationships**:
- `room_id` -> `index.threads.threadID` (conceptual, as `local_events` is the source for `mx_room_messages` which links to `threads`)
- `event_id` -> `index.mx_room_messages.eventID` (direct relationship, though `mx_room_messages` is a processed view)
- `redacts` -> `local_events.event_id` (self-referencing)

### `local_room_account_data`

**Purpose**: Stores per-room account data, used for features like inbox management and tags.

| Column    | Type | NOT NULL | Default | Description                                                                                             |
| --------- | ---- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `room_id` | TEXT | ✅        |         | **Primary Key (with type)**. The Matrix Room ID.                                                        |
| `type`    | TEXT | ✅        |         | **Primary Key (with room_id)**. The type of account data (e.g., `com.beeper.inbox.done`, `m.fully_read`). |
| `content` | TEXT | ✅        |         | The JSON content of the account data.                                                                   |

**Relationships**:
- `room_id` -> `index.threads.threadID` (conceptual)

### `local_current_state_events`

**Purpose**: Tracks the current state of rooms by linking `room_id`, `type`, and `state_key` to the latest `event_id`.

| Column      | Type | NOT NULL | Default | Description                                                                                             |
| ----------- | ---- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `room_id`   | TEXT | ✅        |         | **Primary Key (with type, state_key)**. The Matrix Room ID.                                             |
| `type`      | TEXT | ✅        |         | **Primary Key (with room_id, state_key)**. The type of state event (e.g., `m.room.name`, `m.room.topic`). |
| `state_key` | TEXT | ✅        |         | **Primary Key (with room_id, type)**. The state key for the event.                                      |
| `event_id`  | TEXT | ✅        |         | The `event_id` of the latest state event for this `room_id`, `type`, and `state_key` combination. **Foreign Key** to `local_events.event_id`. |

**Relationships**:
- `event_id` -> `local_events.event_id`

### `local_receipts`

**Purpose**: Stores read receipt information, indicating which events have been read by which users in a room.

| Column            | Type    | NOT NULL | Default | Description                                                                                             |
| ----------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `room_id`         | TEXT    | ✅        |         | **Primary Key (with sender)**. The Matrix Room ID.                                                      |
| `sender`          | TEXT    | ✅        |         | **Primary Key (with room_id)**. The Matrix User ID who sent the read receipt.                           |
| `event_id`        | TEXT    | ✅        |         | The `event_id` of the event that was read. **Foreign Key** to `local_events.event_id`.                  |
| `stream_order`    | INTEGER | ✅        |         | An ordering value for the receipt within the stream.                                                    |
| `stream_suborder` | INTEGER | ✅        |         | A sub-ordering value for the receipt within the stream.                                                 |
| `receipt_ts`      | INTEGER | ✅        |         | The timestamp when the receipt was received.                                                            |
| `backed_up_ts`    | INTEGER |          |         | Timestamp when the receipt was backed up.                                                               |
| `backup_backoff_ts` | INTEGER |          |         | Timestamp for backup retry backoff.                                                                     |

**Relationships**:
- `event_id` -> `local_events.event_id`
- `room_id` -> `index.threads.threadID` (conceptual)

### `account`

**Purpose**: Stores the main user account authentication details for the Beeper Matrix client.

| Column       | Type | NOT NULL | Default | Description                                                                                             |
| ------------ | ---- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `user_id`    | TEXT | ✅        |         | **Primary Key**. The Matrix User ID of the logged-in user (e.g., `@tetmin:beeper.com`).                 |
| `device_id`  | TEXT | ✅        |         | The device ID associated with this session.                                                             |
| `access_token` | TEXT | ✅        |         | The access token used for authenticating with the Matrix homeserver.                                    |
| `homeserver` | TEXT | ✅        |         | The URL of the Matrix homeserver (e.g., `https://matrix.beeper.com/`).                                  |

**Relationships**:
- None explicitly defined, but `user_id` is central to all Matrix-related operations.

### `store`

**Purpose**: A generic key-value store for application-wide settings and bridge states.

| Column  | Type | NOT NULL | Default | Description                                                                                             |
| ------- | ---- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `key`   | TEXT | ✅        |         | **Primary Key**. The unique key for the stored setting (e.g., `ad:com.beeper.desktop.prefs`).           |
| `value` | BLOB |          |         | The value associated with the key, typically a JSON blob containing settings or state information.      |

**Relationships**:
- None. This is a configuration table.

---

## Platform-Specific Databases (`local-*/megabridge.db`)

All platform-specific databases (`local-whatsapp/megabridge.db`, `local-telegram/megabridge.db`, `local-instagram/megabridge.db`, `local-twitter/megabridge.db`, `local-signal/megabridge.db`) share a common core schema for messages, portals (conversations), ghosts (contacts), and user-portal relationships. They then have additional tables specific to the platform's features and protocol.

### Common Core Tables

#### `message`

**Purpose**: Stores platform-native message data, including metadata and links to media.

| Column           | Type    | NOT NULL | Default | Description                                                                                             |
| ---------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `rowid`          | INTEGER | ✅        |         | **Primary Key**. Internal SQLite row ID.                                                                |
| `bridge_id`      | TEXT    | ✅        |         | Identifier for the bridge (e.g., `local-whatsapp`).                                                     |
| `id`             | TEXT    | ✅        |         | Platform-specific message ID.                                                                           |
| `part_id`        | TEXT    | ✅        |         | Part ID for multi-part messages.                                                                        |
| `mxid`           | TEXT    | ✅        |         | The Matrix Event ID associated with this message. **Unique**. **Foreign Key** to `account.local_events.event_id` (conceptual). |
| `room_id`        | TEXT    | ✅        |         | Platform-specific room/chat ID. **Foreign Key** to `portal.id`.                                         |
| `room_receiver`  | TEXT    | ✅        |         | The receiver ID for the room.                                                                           |
| `sender_id`      | TEXT    | ✅        |         | Platform-specific sender ID. **Foreign Key** to `ghost.id`.                                             |
| `sender_mxid`    | TEXT    | ✅        |         | The Matrix User ID of the sender.                                                                       |
| `timestamp`      | BIGINT  | ✅        |         | Unix timestamp (nanoseconds) of the message.                                                            |
| `edit_count`     | INTEGER | ✅        | 0       | Number of times the message has been edited.                                                            |
| `double_puppeted` | BOOLEAN |          |         | Indicates if the message was double-puppeted (sent by the bridge and also by the user directly).        |
| `thread_root_id` | TEXT    |          |         | Platform-specific ID of the root message in a thread.                                                   |
| `reply_to_id`    | TEXT    |          |         | Platform-specific ID of the message being replied to.                                                   |
| `reply_to_part_id` | TEXT    |          |         | Part ID of the message being replied to.                                                                |
| `send_txn_id`    | TEXT    |          |         | Transaction ID for sending the message. **Unique**.                                                     |
| `metadata`       | jsonb   | ✅        |         | JSON blob containing platform-specific metadata, including media details (keys, paths, mime types).     |

**Relationships**:
- `(bridge_id, room_id, room_receiver)` -> `portal.(bridge_id, id, receiver)` (CASCADE DELETE/UPDATE)
- `(bridge_id, sender_id)` -> `ghost.(bridge_id, id)` (CASCADE DELETE/UPDATE)
- `mxid` -> `account.local_events.event_id` (conceptual, as `mxid` is the Matrix event ID)
- `reply_to_id` -> `message.id` (self-referencing)

#### `portal`

**Purpose**: Stores information about conversations or chat rooms on the specific platform.

| Column          | Type    | NOT NULL | Default | Description                                                                                             |
| --------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `bridge_id`     | TEXT    | ✅        |         | **Primary Key (with id, receiver)**. Identifier for the bridge.                                         |
| `id`            | TEXT    | ✅        |         | **Primary Key (with bridge_id, receiver)**. Platform-specific portal/room ID.                           |
| `receiver`      | TEXT    | ✅        |         | **Primary Key (with bridge_id, id)**. The receiver ID for the portal.                                   |
| `mxid`          | TEXT    |          |         | The Matrix Room ID associated with this portal. **Unique**. **Foreign Key** to `index.threads.threadID` (conceptual). |
| `parent_id`     | TEXT    |          |         | Platform-specific ID of the parent portal (for spaces/communities).                                     |
| `parent_receiver` | TEXT    | ✅        | ''      | Receiver ID of the parent portal.                                                                       |
| `relay_bridge_id` | TEXT    |          |         | Bridge ID of the relay user.                                                                            |
| `relay_login_id`  | TEXT    |          |         | Login ID of the relay user. **Foreign Key** to `user_login.id`.                                         |
| `other_user_id` | TEXT    |          |         | For DM portals, the ID of the other user.                                                               |
| `name`          | TEXT    | ✅        |         | Display name of the portal/chat.                                                                        |
| `topic`         | TEXT    | ✅        |         | Topic or description of the portal/chat.                                                                |
| `avatar_id`     | TEXT    | ✅        |         | Platform-specific ID for the avatar.                                                                    |
| `avatar_hash`   | TEXT    | ✅        |         | Hash of the avatar.                                                                                     |
| `avatar_mxc`    | TEXT    | ✅        |         | Matrix Content URI for the avatar.                                                                      |
| `name_set`      | BOOLEAN | ✅        |         | Indicates if the name has been set.                                                                     |
| `avatar_set`    | BOOLEAN | ✅        |         | Indicates if the avatar has been set.                                                                   |
| `topic_set`     | BOOLEAN | ✅        |         | Indicates if the topic has been set.                                                                    |
| `name_is_custom` | BOOLEAN | ✅        | false   | Indicates if the name is custom.                                                                        |
| `in_space`      | BOOLEAN | ✅        |         | Indicates if the portal is part of a space.                                                             |
| `room_type`     | TEXT    | ✅        |         | Type of room (e.g., `dm`, `group`, `space`).                                                            |
| `disappear_type` | TEXT    |          |         | Type of disappearing messages.                                                                          |
| `disappear_timer` | BIGINT  |          |         | Timer for disappearing messages.                                                                        |
| `cap_state`     | jsonb   |          |         | Capabilities state of the portal.                                                                       |
| `metadata`      | jsonb   | ✅        |         | JSON blob for additional platform-specific metadata.                                                    |

**Relationships**:
- `(bridge_id, parent_id, parent_receiver)` -> `portal.(bridge_id, id, receiver)` (self-referencing, no CASCADE DELETE)
- `(relay_bridge_id, relay_login_id)` -> `user_login.(bridge_id, id)` (SET NULL on DELETE)
- `mxid` -> `index.threads.threadID` (conceptual)

#### `ghost`

**Purpose**: Stores contact or user information from the specific platform.

| Column          | Type    | NOT NULL | Default | Description                                                                                             |
| --------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `bridge_id`     | TEXT    | ✅        |         | **Primary Key (with id)**. Identifier for the bridge.                                                   |
| `id`            | TEXT    | ✅        |         | **Primary Key (with bridge_id)**. Platform-specific user/contact ID.                                    |
| `name`          | TEXT    | ✅        |         | Display name of the contact.                                                                            |
| `avatar_id`     | TEXT    | ✅        |         | Platform-specific ID for the avatar.                                                                    |
| `avatar_hash`   | TEXT    | ✅        |         | Hash of the avatar.                                                                                     |
| `avatar_mxc`    | TEXT    | ✅        |         | Matrix Content URI for the avatar.                                                                      |
| `name_set`      | BOOLEAN | ✅        |         | Indicates if the name has been set.                                                                     |
| `avatar_set`    | BOOLEAN | ✅        |         | Indicates if the avatar has been set.                                                                   |
| `contact_info_set` | BOOLEAN | ✅        |         | Indicates if contact information has been set.                                                          |
| `is_bot`        | BOOLEAN | ✅        |         | Indicates if the contact is a bot.                                                                      |
| `identifiers`   | jsonb   | ✅        |         | JSON array of identifiers for the contact (e.g., phone numbers, usernames).                             |
| `metadata`      | jsonb   | ✅        |         | JSON blob for additional platform-specific metadata.                                                    |

**Relationships**:
- `(bridge_id, id)` -> `message.sender_id` (CASCADE DELETE/UPDATE)

#### `user_portal`

**Purpose**: Maps users to the portals (conversations) they are part of, including read status.

| Column          | Type    | NOT NULL | Default | Description                                                                                             |
| --------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `bridge_id`     | TEXT    | ✅        |         | **Primary Key (with user_mxid, login_id, portal_id, portal_receiver)**. Identifier for the bridge.      |
| `user_mxid`     | TEXT    | ✅        |         | **Primary Key (with bridge_id, login_id, portal_id, portal_receiver)**. The Matrix User ID.             |
| `login_id`      | TEXT    | ✅        |         | **Primary Key (with bridge_id, user_mxid, portal_id, portal_receiver)**. The login ID. **Foreign Key** to `user_login.id`. |
| `portal_id`     | TEXT    | ✅        |         | **Primary Key (with bridge_id, user_mxid, login_id, portal_receiver)**. Platform-specific portal/room ID. **Foreign Key** to `portal.id`. |
| `portal_receiver` | TEXT    | ✅        |         | **Primary Key (with bridge_id, user_mxid, login_id, portal_id)**. The receiver ID for the portal.       |
| `in_space`      | BOOLEAN | ✅        |         | Indicates if the user is in a space.                                                                    |
| `preferred`     | BOOLEAN | ✅        |         | Indicates if this is the preferred user-portal mapping.                                                 |
| `last_read`     | BIGINT  |          |         | Timestamp of the last message read by this user in this portal.                                         |

**Relationships**:
- `(bridge_id, login_id)` -> `user_login.(bridge_id, id)` (CASCADE DELETE/UPDATE)
- `(bridge_id, portal_id, portal_receiver)` -> `portal.(bridge_id, id, receiver)` (CASCADE DELETE/UPDATE)

### WhatsApp Specific Tables

#### `whatsmeow_contacts`

**Purpose**: Stores contact information specific to WhatsApp, including names and JIDs.

| Column        | Type | NOT NULL | Default | Description                                                                                             |
| ------------- | ---- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `our_jid`     | TEXT |          |         | The JID (Jabber ID) of our WhatsApp account. **Primary Key (with their_jid)**. **Foreign Key** to `whatsmeow_device.jid`. |
| `their_jid`   | TEXT |          |         | The JID of the contact. **Primary Key (with our_jid)**.                                               |
| `first_name`  | TEXT |          |         | The first name of the contact.                                                                          |
| `full_name`   | TEXT |          |         | The full name of the contact.                                                                           |
| `push_name`   | TEXT |          |         | The push name of the contact.                                                                           |
| `business_name` | TEXT |          |         | The business name of the contact, if applicable.                                                        |

**Relationships**:
- `our_jid` -> `whatsmeow_device.jid` (CASCADE DELETE/UPDATE)

#### `whatsmeow_sessions`

**Purpose**: Stores session data for WhatsApp, likely related to encryption and communication sessions.

| Column     | Type  | NOT NULL | Default | Description                                                                                             |
| ---------- | ----- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `our_jid`  | TEXT  |          |         | The JID of our WhatsApp account. **Primary Key (with their_id)**. **Foreign Key** to `whatsmeow_device.jid`. |
| `their_id` | TEXT  |          |         | The ID of the other party in the session. **Primary Key (with our_jid)**.                             |
| `session`  | bytea |          |         | The session data, likely encrypted or serialized.                                                       |

**Relationships**:
- `our_jid` -> `whatsmeow_device.jid` (CASCADE DELETE/UPDATE)

#### `whatsmeow_device`

**Purpose**: Stores device-specific information and cryptographic keys for the WhatsApp account.

| Column              | Type    | NOT NULL | Default | Description                                                                                             |
| ------------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `jid`               | TEXT    | ✅        |         | **Primary Key**. The JID (Jabber ID) of the WhatsApp device.                                            |
| `lid`               | TEXT    |          |         | Linked ID.                                                                                              |
| `facebook_uuid`     | uuid    |          |         | Facebook UUID associated with the device.                                                               |
| `registration_id`   | BIGINT  | ✅        |         | Device registration ID (0 to 4294967295).                                                               |
| `noise_key`         | bytea   | ✅        |         | Cryptographic noise key (32 bytes).                                                                     |
| `identity_key`      | bytea   | ✅        |         | Cryptographic identity key (32 bytes).                                                                  |
| `signed_pre_key`    | bytea   | ✅        |         | Signed pre-key (32 bytes).                                                                              |
| `signed_pre_key_id` | INTEGER | ✅        |         | ID of the signed pre-key (0 to 16777215).                                                               |
| `signed_pre_key_sig` | bytea   | ✅        |         | Signature of the signed pre-key (64 bytes).                                                             |
| `adv_key`           | bytea   | ✅        |         | Advanced key.                                                                                           |
| `adv_details`       | bytea   | ✅        |         | Advanced details.                                                                                       |
| `adv_account_sig`   | bytea   | ✅        |         | Advanced account signature (64 bytes).                                                                  |
| `adv_account_sig_key` | bytea   | ✅        |         | Advanced account signature key (32 bytes).                                                              |
| `adv_device_sig`    | bytea   | ✅        |         | Advanced device signature (64 bytes).                                                                   |
| `platform`          | TEXT    | ✅        | ''      | The platform of the device.                                                                             |
| `business_name`     | TEXT    | ✅        | ''      | The business name associated with the device.                                                           |
| `push_name`         | TEXT    | ✅        | ''      | The push name associated with the device.                                                               |
| `lid_migration_ts`  | BIGINT  | ✅        | 0       | Timestamp of LID migration.                                                                             |

**Relationships**:
- `jid` -> `whatsmeow_contacts.our_jid` (CASCADE DELETE/UPDATE)
- `jid` -> `whatsmeow_sessions.our_jid` (CASCADE DELETE/UPDATE)

### Telegram Specific Tables

#### `telegram_user_state`

**Purpose**: Stores the state of Telegram users, likely related to message synchronization and sequence numbers.

| Column    | Type   | NOT NULL | Default | Description                                                                                             |
| --------- | ------ | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `user_id` | BIGINT | ✅        |         | **Primary Key**. The Telegram user ID.                                                                  |
| `pts`     | BIGINT | ✅        |         | Points (updates) timestamp.                                                                             |
| `qts`     | BIGINT | ✅        |         | QTS (updates) timestamp.                                                                                |
| `date`    | BIGINT | ✅        |         | Date of the state.                                                                                      |
| `seq`     | BIGINT | ✅        |         | Sequence number.                                                                                        |

**Relationships**:
- None explicitly defined.

#### `telegram_channel_state`

**Purpose**: Stores the state of Telegram channels for specific users, likely for message synchronization within channels.

| Column     | Type   | NOT NULL | Default | Description                                                                                             |
| ---------- | ------ | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `user_id`  | BIGINT | ✅        |         | **Primary Key (with channel_id)**. The Telegram user ID.                                                |
| `channel_id` | BIGINT | ✅        |         | **Primary Key (with user_id)**. The Telegram channel ID.                                                |
| `pts`      | BIGINT | ✅        |         | Points (updates) timestamp for the channel.                                                             |

**Relationships**:
- `user_id` -> `telegram_user_state.user_id` (conceptual)

### Instagram Specific Tables

#### `meta_thread`

**Purpose**: Stores information about Instagram threads, linking parent threads to sub-threads or messages.

| Column     | Type   | NOT NULL | Default | Description                                                                                             |
| ---------- | ------ | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `parent_key` | BIGINT | ✅        |         | The key of the parent thread.                                                                           |
| `thread_key` | BIGINT | ✅        |         | **Primary Key**. The unique key for this thread.                                                        |
| `message_id` | TEXT   | ✅        |         | The message ID associated with this thread. **Unique**.                                                 |

**Relationships**:
- None explicitly defined, but `message_id` likely relates to `message.id` in the common core tables.

### Signal Specific Tables

#### `signalmeow_recipients`

**Purpose**: Stores information about Signal recipients, including their identifiers, contact details, and profile information.

| Column              | Type    | NOT NULL | Default | Description                                                                                             |
| ------------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `account_id`        | TEXT    | ✅        |         | The account ID this recipient belongs to. **Foreign Key** to `signalmeow_device.aci_uuid`.              |
| `aci_uuid`          | TEXT    |          |         | The ACI (Account ID) UUID of the recipient. **Unique (with account_id)**.                               |
| `pni_uuid`          | TEXT    |          |         | The PNI (Phone Number Identifier) UUID of the recipient. **Unique (with account_id)**.                  |
| `e164_number`       | TEXT    | ✅        | ''      | The E.164 formatted phone number of the recipient.                                                      |
| `contact_name`      | TEXT    | ✅        | ''      | The contact name of the recipient.                                                                      |
| `contact_avatar_hash` | TEXT    | ✅        | ''      | Hash of the contact's avatar.                                                                           |
| `profile_key`       | bytea   |          |         | The profile key of the recipient.                                                                       |
| `profile_name`      | TEXT    | ✅        | ''      | The profile name of the recipient.                                                                      |
| `profile_about`     | TEXT    | ✅        | ''      | The 'about' text from the recipient's profile.                                                          |
| `profile_about_emoji` | TEXT    | ✅        | ''      | Emoji associated with the recipient's 'about' text.                                                     |
| `profile_avatar_path` | TEXT    | ✅        | ''      | Path to the recipient's profile avatar.                                                                 |
| `profile_fetched_at` | BIGINT  |          |         | Timestamp when the profile was last fetched.                                                            |
| `needs_pni_signature` | BOOLEAN | ✅        | false   | Indicates if a PNI signature is needed.                                                                 |

**Relationships**:
- `account_id` -> `signalmeow_device.aci_uuid` (CASCADE DELETE/UPDATE)

#### `signalmeow_device`

**Purpose**: Stores device-specific cryptographic and account information for Signal.

| Column                | Type    | NOT NULL | Default | Description                                                                                             |
| --------------------- | ------- | -------- | ------- | ------------------------------------------------------------------------------------------------------- |
| `aci_uuid`            | TEXT    | ✅        |         | **Primary Key**. The ACI (Account ID) UUID of the device.                                               |
| `aci_identity_key_pair` | bytea   | ✅        |         | The identity key pair for the ACI.                                                                      |
| `registration_id`     | INTEGER | ✅        |         | The registration ID (0 to 4294967295).                                                                  |
| `pni_uuid`            | TEXT    | ✅        |         | The PNI (Phone Number Identifier) UUID.                                                                 |
| `pni_identity_key_pair` | bytea   | ✅        |         | The identity key pair for the PNI.                                                                      |
| `pni_registration_id` | INTEGER | ✅        |         | The PNI registration ID (0 to 4294967295).                                                              |
| `device_id`           | INTEGER | ✅        |         | The device ID.                                                                                          |
| `number`              | TEXT    | ✅        | ''      | The phone number associated with the device.                                                            |
| `password`            | TEXT    | ✅        | ''      | The password for the device.                                                                            |
| `master_key`          | bytea   |          |         | The master key.                                                                                         |
| `account_record`      | bytea   |          |         | The account record.                                                                                     |
| `account_entropy_pool` | TEXT    |          |         | The account entropy pool.                                                                               |
| `ephemeral_backup_key` | bytea   |          |         | The ephemeral backup key.                                                                               |
| `media_root_backup_key` | bytea   |          |         | The media root backup key.                                                                              |

**Relationships**:
- `aci_uuid` -> `signalmeow_recipients.account_id` (CASCADE DELETE/UPDATE)
