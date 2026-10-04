package com.shopping.advisor.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;
import java.io.Serializable;

@Entity
@Table(name = "products")
@Data
public class Product implements Serializable {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String productName;

    @Column(columnDefinition = "TEXT")
    private String sourceUrl;

    @Column(columnDefinition = "TEXT")
    private String imageUrl; 

    private Double initialPrice;
    
    private String currency;

    private LocalDateTime createdAt = LocalDateTime.now();

    // Bir məhsulun çoxlu rəqib qiymətləri ola bilər
    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL,fetch = FetchType.EAGER)
    private List<CompetitorPrice> competitorPrices;

    private static final long serialVersionUID = 1L;
}