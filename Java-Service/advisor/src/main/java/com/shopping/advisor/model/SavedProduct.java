package com.shopping.advisor.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "saved_products")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SavedProduct {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String customTitle; // İstifadəçinin verdiyi/redaktə etdiyi ad

    @Column(columnDefinition = "TEXT")
    private String imageUrl; // Şəklin URL-i

    @Column(columnDefinition = "TEXT")
    private String sourceUrl; // Məhsulun orijinal səhifə linki

    private BigDecimal price; // O anki qiyməti

    @Column(columnDefinition = "TEXT")
    private String note; // "Niyə almaq istəyirəm?" qeydi

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "category_id")
    private Category category; // Aid olduğu kateqoriya

    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
    }

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;
}