package com.shopping.advisor.repository;

import com.shopping.advisor.model.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
public interface ProductRepository extends JpaRepository<Product, Long> {
    Optional<Product> findByProductName(String productName);
}