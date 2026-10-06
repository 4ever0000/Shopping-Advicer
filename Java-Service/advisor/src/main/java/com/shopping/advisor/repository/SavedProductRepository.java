package com.shopping.advisor.repository;

import com.shopping.advisor.model.SavedProduct;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface SavedProductRepository extends JpaRepository<SavedProduct, Long> {
    List<SavedProduct> findByCategoryId(Long categoryId);
    List<SavedProduct> findByCategoryNameIgnoreCase(String categoryName);
}