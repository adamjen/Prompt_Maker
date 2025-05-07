graph TD
    A[User] --> B[Flask API]
    B --> C{Orchestrator}
    C --> D[Topic Analysis Agent]
    C --> E[Category Breakdown Agent]
    C --> F[Iterative Refinement Agent]
    C --> G[Research Integration Agent]
    G --> H[External Research API]
    C --> I[Configuration Manager]
    
    style A fill:#FFE4B5,stroke:#333
    style B fill:#87CEEB,stroke:#333
    style C fill:#98FB98,stroke:#333
    style D fill:#FFB6C1,stroke:#333
    style E fill:#FFB6C1,stroke:#333
    style F fill:#FFB6C1,stroke:#333
    style G fill:#FFB6C1,stroke:#333
    style H fill:#DDA0DD,stroke:#333
    style I fill:#FFFF99,stroke:#333
    
    classDef component fill:#87CEEB,stroke:#333;
    classDef agent fill:#FFB6C1,stroke:#333;
    classDef infrastructure fill:#FFFF99,stroke:#333;
</code>