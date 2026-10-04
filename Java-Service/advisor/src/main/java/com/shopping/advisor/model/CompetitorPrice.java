package com.shopping.advisor.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.io.Serializable;
import java.util.List;
@Entity
@Table(name = "competitor_prices")
@Data
public class CompetitorPrice implements  Serializable {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // Hansı məhsulun rəqib qiymətidir? (Foreign Key)
    @ManyToOne
    @JoinColumn(name = "product_id", nullable = false)
    @JsonIgnore
    private Product product;

    private String platformName; 
    
    @Column(columnDefinition = "TEXT")
    private String competitorUrl; // Tapılan ucuz məhsulun linki

    @Column(columnDefinition = "TEXT")
    private String imageUrl;

    @ElementCollection
    @CollectionTable(name = "competitor_comments", joinColumns = @JoinColumn(name = "competitor_price_id"))
    @Column(name = "comment", columnDefinition = "TEXT")
    private List<String> comments; // 3 rəy/yorum siyahısı
    
    private Double price;

    private String currency; // Əlavə olundu: AZN, TL və s.
    
    private LocalDateTime foundAt = LocalDateTime.now();

    private static final long serialVersionUID = 1L;
}