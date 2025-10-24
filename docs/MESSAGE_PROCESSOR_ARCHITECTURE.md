# Архитектура MessageProcessor

## Диаграмма потока обработки сообщений

```mermaid
flowchart TD
    Start([Новое сообщение из Telethon]) --> Monitor[ChannelMonitor]
    Monitor --> Validate{Валидное<br/>сообщение?}
    
    Validate -->|Нет| Skip1[Пропустить]
    Validate -->|Да| Dedup{Дедупликация}
    
    Dedup -->|Дубликат| Skip2[Пропустить]
    Dedup -->|Уникальное| Keywords{Фильтр по<br/>ключевым словам}
    
    Keywords -->|Не совпадает| Skip3[Пропустить]
    Keywords -->|Совпадает| Processor[MessageProcessor.process_message]
    
    Processor --> Extract[Извлечение данных]
    
    Extract --> ExtractText[Извлечь текст]
    Extract --> ExtractMedia[Извлечь медиа]
    Extract --> ExtractMeta[Извлечь метаданные]
    
    ExtractText --> PydanticVal{Pydantic<br/>валидация}
    ExtractMedia --> PydanticVal
    ExtractMeta --> PydanticVal
    
    PydanticVal -->|Ошибка| Error1[Логировать ошибку]
    PydanticVal -->|OK| DBCheck{Проверка<br/>в БД}
    
    DBCheck -->|Дубликат| Skip4[Пропустить]
    DBCheck -->|Уникальное| ExtractContacts[Извлечь контакты]
    
    ExtractContacts --> ContactEntities[Из entities]
    ExtractContacts --> ContactText[Из текста regex]
    ExtractContacts --> ContactForward[Из forward info]
    
    ContactEntities --> ContactVal{ContactInfo<br/>валидация}
    ContactText --> ContactVal
    ContactForward --> ContactVal
    
    ContactVal -->|Ошибка| NoContacts[Без контактов]
    ContactVal -->|OK| WithContacts[С контактами]
    
    NoContacts --> SaveDB[Сохранить в БД]
    WithContacts --> SaveDB
    
    SaveDB --> CreatePost[Создать Post]
    SaveDB --> CreateContact[Создать SellerContact]
    SaveDB --> UpdateStats[Обновить статистику]
    
    CreatePost --> Commit{Commit<br/>транзакции}
    CreateContact --> Commit
    UpdateStats --> Commit
    
    Commit -->|Ошибка| Rollback[Rollback]
    Commit -->|OK| AIQueue[TODO: Celery task]
    
    AIQueue --> Complete([✅ Пост сохранен])
    
    Error1 --> End([Конец])
    Skip1 --> End
    Skip2 --> End
    Skip3 --> End
    Skip4 --> End
    Rollback --> End
```

## Архитектура компонентов

```mermaid
classDiagram
    class ChannelMonitor {
        +MessageProcessor message_processor
        +_handle_new_message(event)
        +_process_message(message, channel)
    }
    
    class MessageProcessor {
        +process_message(message, channel, session)
        -_extract_message_data(message, channel)
        -_extract_contacts(message)
        -_is_duplicate(data, channel, session)
        -_check_keywords(text, keywords)
        -_extract_media_info(message)
        -_save_to_database(data, channel, session)
    }
    
    class MessageData {
        +int message_id
        +str channel_id
        +str text
        +MediaInfo media
        +ContactInfo contacts
        +str message_link
        +datetime date
        +validate_text()
    }
    
    class ContactInfo {
        +str telegram_username
        +int telegram_user_id
        +str phone_number
        +str other_contacts
        +validate_username()
        +validate_phone()
        +check_has_contact()
    }
    
    class MediaInfo {
        +bool has_photo
        +bool has_document
        +int photo_count
        +int media_group_id
    }
    
    class Post {
        +int id
        +int source_channel_id
        +int original_message_id
        +str original_text
        +bool is_selling_post
        +bool published
    }
    
    class SellerContact {
        +int id
        +int post_id
        +str telegram_username
        +int telegram_user_id
        +str phone_number
    }
    
    class Channel {
        +int id
        +str channel_id
        +List keywords
        +int total_posts
    }
    
    ChannelMonitor --> MessageProcessor : uses
    MessageProcessor --> MessageData : creates
    MessageProcessor --> ContactInfo : creates
    MessageProcessor --> MediaInfo : creates
    MessageData --> ContactInfo : contains
    MessageData --> MediaInfo : contains
    MessageProcessor --> Post : creates
    MessageProcessor --> SellerContact : creates
    MessageProcessor --> Channel : reads
    Post --> SellerContact : has one
    Post --> Channel : belongs to
```

## Извлечение контактов

```mermaid
flowchart LR
    Message[Telegram Message] --> Sources{Источники<br/>контактов}
    
    Sources --> Entities[Message Entities]
    Sources --> Text[Message Text]
    Sources --> Forward[Forward Info]
    
    Entities --> EntityPhone[MessageEntityPhone]
    Entities --> EntityMention[Mention entities]
    
    Text --> RegexUsername[Regex: @username]
    Text --> RegexPhone[Regex: phone patterns]
    Text --> RegexEmail[Regex: email]
    
    Forward --> ForwardUser[Forward from user]
    
    EntityPhone --> Normalize[Нормализация]
    EntityMention --> Normalize
    RegexUsername --> Normalize
    RegexPhone --> Normalize
    RegexEmail --> Normalize
    ForwardUser --> Normalize
    
    Normalize --> Validate{Pydantic<br/>ContactInfo}
    
    Validate -->|Валидно| Contact[ContactInfo]
    Validate -->|Невалидно| None[None]
    
    Contact --> Save[Сохранить в БД]
```

## Валидация данных с Pydantic

```mermaid
flowchart TD
    Input[Raw Data] --> Field1[Field Validators]
    
    Field1 --> Username[@field_validator username]
    Field1 --> Phone[@field_validator phone]
    
    Username --> CleanUsername[Удалить @]
    Phone --> NormalizePhone[Добавить +, форматировать]
    
    CleanUsername --> Model[@model_validator]
    NormalizePhone --> Model
    
    Model --> CheckContact[check_has_contact]
    
    CheckContact -->|Нет контактов| ValidationError[ValidationError]
    CheckContact -->|OK| Validated[✅ Validated Data]
    
    Validated --> Serialize{Serialization}
    
    Serialize --> Dict[model_dump]
    Serialize --> JSON[model_dump_json]
```

## База данных: связи между таблицами

```mermaid
erDiagram
    CHANNELS ||--o{ POSTS : "has many"
    POSTS ||--o| SELLER_CONTACTS : "has one"
    POSTS ||--o| CAR_DATA : "has one"
    USERS ||--o{ CONTACT_REQUESTS : "makes"
    POSTS ||--o{ CONTACT_REQUESTS : "for"
    
    CHANNELS {
        int id PK
        string channel_id UK
        string channel_username
        string channel_title
        bool is_active
        array keywords
        int total_posts
        int published_posts
    }
    
    POSTS {
        int id PK
        int source_channel_id FK
        int original_message_id
        string original_message_link
        text original_text
        text processed_text
        bool is_selling_post
        float confidence_score
        bool published
        datetime date_found
        datetime date_processed
    }
    
    SELLER_CONTACTS {
        int id PK
        int post_id FK
        string telegram_username
        bigint telegram_user_id
        string phone_number
        text other_contacts
    }
    
    CAR_DATA {
        int id PK
        int post_id FK
        string brand
        string model
        int year
        string transmission
        int price
    }
    
    USERS {
        int id PK
        bigint telegram_user_id UK
        string username
        string first_name
    }
    
    CONTACT_REQUESTS {
        int id PK
        int user_id FK
        int post_id FK
        datetime date_requested
    }
```

## Интеграция с ChannelMonitor

```mermaid
sequenceDiagram
    participant TG as Telegram
    participant CM as ChannelMonitor
    participant MP as MessageProcessor
    participant PD as Pydantic Models
    participant DB as Database
    
    TG->>CM: NewMessage event
    CM->>CM: _handle_new_message()
    
    CM->>CM: Validate message
    CM->>CM: Check deduplicator
    CM->>CM: Check keywords
    
    CM->>MP: process_message(msg, channel, session)
    
    MP->>MP: _extract_message_data()
    MP->>PD: Validate MessageData
    PD-->>MP: Valid data
    
    MP->>DB: Check duplicate
    DB-->>MP: Not duplicate
    
    MP->>MP: _extract_contacts()
    MP->>PD: Validate ContactInfo
    PD-->>MP: Valid contacts
    
    MP->>DB: _save_to_database()
    
    DB->>DB: Create Post
    DB->>DB: Create SellerContact
    DB->>DB: Update Channel stats
    DB->>DB: Commit transaction
    
    DB-->>MP: Post created
    MP-->>CM: Post object
    
    CM->>CM: Log success
    
    Note over MP,DB: TODO: Send to Celery queue
```

## Обработка ошибок

```mermaid
flowchart TD
    Start[Process Message] --> Try{Try}
    
    Try --> Extract[Extract Data]
    
    Extract -->|Success| Validate{Pydantic<br/>Validation}
    Extract -->|Exception| CatchError1[Catch Exception]
    
    Validate -->|Valid| DBOps[Database Operations]
    Validate -->|ValidationError| CatchError2[Catch ValidationError]
    
    DBOps -->|Success| Commit{Commit}
    DBOps -->|Exception| CatchError3[Catch DB Exception]
    
    Commit -->|Success| Return[Return Post]
    Commit -->|Exception| Rollback[Rollback]
    
    CatchError1 --> Log1[Log Error]
    CatchError2 --> Log2[Log ValidationError]
    CatchError3 --> Log3[Log DB Error]
    Rollback --> Log4[Log Rollback]
    
    Log1 --> ReturnNone[Return None]
    Log2 --> ReturnNone
    Log3 --> ReturnNone
    Log4 --> ReturnNone
    
    Return --> End([Success])
    ReturnNone --> End
```

## Производительность: оптимизации

```mermaid
mindmap
  root((Message<br/>Processor<br/>Performance))
    Regex
      Compiled patterns
      Class-level cache
      Efficient patterns
    Database
      Minimal queries
      Batch operations
      Proper indexes
    Async
      await IO operations
      Non-blocking calls
      Concurrent processing
    Pydantic
      Rust core
      Type coercion
      Fast validation
    Memory
      Small footprint
      No data duplication
      Efficient structures
```

## Тестовое покрытие

```mermaid
pie title Test Coverage by Component
    "Pydantic Models" : 17
    "Contact Extraction" : 10
    "Keyword Filtering" : 4
    "Duplicate Detection" : 2
    "Media Processing" : 2
```

---

**Легенда:**
- 🟢 **Зеленый** - Успешное выполнение
- 🔴 **Красный** - Ошибка/исключение
- 🟡 **Желтый** - Условие/проверка
- 🔵 **Синий** - Процесс/операция


