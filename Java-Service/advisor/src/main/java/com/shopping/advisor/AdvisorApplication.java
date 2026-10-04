
package com.shopping.advisor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching; 

@SpringBootApplication
@EnableCaching 
public class AdvisorApplication {

    public static void main(String[] args) {
        SpringApplication.run(AdvisorApplication.class, args);
    }

}