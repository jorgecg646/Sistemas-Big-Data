CREATE DATABASE fila_2;

USE fila_2;

CREATE TABLE IPV (id INT AUTO_INCREMENT PRIMARY KEY,
                  COD VARCHAR(20) NOT NULL,
                  Nombre VARCHAR(200) NOT NULL);



CREATE TABLE data_ipv (id INT AUTO_INCREMENT PRIMARY KEY,
                        Fecha VARCHAR(200) NOT NULL,
                              FK_Periodo INT,
                              Anyo VARCHAR(5),
                              Valor FLOAT,
                              Id_ipv INT,
                              FOREIGN KEY (Id_ipv) REFERENCES ipv (id));



CREATE TABLE IPC (id INT AUTO_INCREMENT PRIMARY KEY,
                  COD VARCHAR(20) NOT NULL,
                  Nombre VARCHAR(200) NOT NULL);



CREATE TABLE data_ipc (id INT AUTO_INCREMENT PRIMARY KEY,
                        Fecha VARCHAR(200) NOT NULL,
                              FK_Periodo INT,
                              Anyo VARCHAR(5),
                              Valor FLOAT,
                              Id_ipc INT,
                              FOREIGN KEY (Id_ipc) REFERENCES ipc (id));