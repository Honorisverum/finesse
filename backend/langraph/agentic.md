```mermaid
stateDiagram-v2
    [*] --> START
    
    START --> InterestedFlirt: Поддержать разговор о кофе/обсудить ее работу
    START --> FAIL: Сразу пригласить на свидание
    
    InterestedFlirt --> HintAtSecret: Заметить, что она не пьет кофе сама
    InterestedFlirt --> ArtConversation: Упомянуть искусство, особенно авангард
    InterestedFlirt --> FAIL: Сделать грубый комплимент внешности
    
    HintAtSecret --> ConfidentialTalk: Аккуратно спросить почему не пьет кофе
    HintAtSecret --> FAIL: Настойчиво расспрашивать о секрете
    
    ArtConversation --> DeepConversation: Показать знания в области авангарда
    ArtConversation --> InterestedFlirt: Поверхностные знания об искусстве
    
    DeepConversation --> EscapePlan: Предложить обойти менеджера и встретиться
    DeepConversation --> FAIL: Слишком прямолинейно пригласить на свидание
    
    ConfidentialTalk --> EscapePlan: Предложить обойти менеджера и встретиться
    ConfidentialTalk --> FAIL: Неуместно пошутить про кофе
    
    EscapePlan --> SUCCESS: Предложить креативный способ встречи вне кафе
    EscapePlan --> FAIL: Предложить что-то слишком рискованное

    style START fill:#FFA500,stroke:#333,stroke-width:2px
```