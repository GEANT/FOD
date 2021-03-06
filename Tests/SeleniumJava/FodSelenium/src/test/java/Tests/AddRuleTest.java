package test.java.Tests;

import java.io.FileWriter;
import java.io.IOException;
import java.util.concurrent.TimeUnit;
import dataProvider.ConfigFileReader;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.AfterClass;


public class AddRuleTest {
 
        static WebDriver driver;

        static String url;
        
        static ConfigFileReader configFileReader = new ConfigFileReader();
        
        public static void Login() 
        {
        	driver.get(url);
			driver.findElement(By.id("id_username")).click();
			driver.findElement(By.id("id_username")).sendKeys(configFileReader.getUserLogin());
			driver.findElement(By.id("id_password")).click();
			driver.findElement(By.id("id_password")).sendKeys(configFileReader.getUserPassword());
			driver.findElement(By.id("applybutton")).click();
        }

	@Test
	//public static void AddName(WebDriver driver, String url) 
	public static void AddName() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			driver.findElement(By.id("applybutton")).click();
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongName(WebDriver driver, String url) 
	public static void AddWrongName() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("1' or '1' = '1 /*");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.id("name_error_id"));
			
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongName(WebDriver driver, String url) 
	public static void AddNoName() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("");
			driver.findElement(By.id("applybutton")).click();
			driver.findElements(By.xpath("//span[@class = 'required']//..//..//label"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongSourceAddress(WebDriver driver, String url) 
	public static void AddWrongSourceAddress() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("efefef");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.id("source_error_id"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongDestinationAddress(WebDriver driver, String url) 
	public static void AddWrongDestinationAddress() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("drgr");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.id("destination_error_id"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWithOutExpires(WebDriver driver, String url) 
	public static void AddWithOutExpires() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			
			driver.findElement(By.id("id_expires")).click();
			driver.findElement(By.id("id_expires")).clear();
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.xpath("//*[contains(text(), 'This field is required.')]"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongSrcPort(WebDriver driver, String url) 
	public static void AddWrongSrcPort() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			
			driver.findElement(By.id("id_sourceport")).click();
			driver.findElement(By.id("id_sourceport")).sendKeys("f//");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.id("sourceport_error_id"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongDestPort(WebDriver driver, String url) 
	public static void AddWrongDestPort() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			
			driver.findElement(By.id("id_destinationport")).click();
			driver.findElement(By.id("id_destinationport")).sendKeys("f//");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.id("destinationport_error_id"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
	@Test
	//public static void AddWrongPort(WebDriver driver, String url) 
	public static void AddWrongPort() 
        {
		try {
			Login();
			driver.findElement(By.id("myrulesheader"));
			driver.findElement(By.id("routebutton")).click();
			driver.findElement(By.id("apply_rule_header_id"));
			driver.findElement(By.id("id_name")).click();
			driver.findElement(By.id("id_name")).sendKeys("npattack");
			driver.findElement(By.id("id_source")).click();
			driver.findElement(By.id("id_source")).sendKeys("0.0.0.0/0");
			driver.findElement(By.id("id_destination")).click();
			driver.findElement(By.id("id_destination")).sendKeys("0.0.0.0/29");
			
			driver.findElement(By.id("id_port")).click();
			driver.findElement(By.id("id_port")).sendKeys("f//");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.id("port_error_id"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
                        throw(e);
		}
	}
	
        @BeforeClass 
        static void testSetUp() {

    		//setting the driver executable
    		System.setProperty("webdriver.chrome.driver", configFileReader.getDriverPath());
		
		
		ChromeOptions chromeOptions = new ChromeOptions();
		//chromeOptions.addArguments("headless");
		//Initiating your chromedriver
		driver=new ChromeDriver(chromeOptions);
		
		
		//Applied wait time
		driver.manage().timeouts().implicitlyWait(5, TimeUnit.SECONDS);
		//maximize window
		driver.manage().window().maximize();
		
		url = configFileReader.getApplicationUrl() + "/altlogin";;
        }

	
        public static void main(String[] args) {
 
                testSetUp();
		

		AddName();


		AddWrongName();


		AddWrongSourceAddress();


		AddWrongDestinationAddress();


		AddWithOutExpires();


		AddWrongSrcPort();


		AddWrongDestPort();


		AddWrongPort();


                testSetDown();
          }
		
        @AfterClass 
        static void testSetDown() {
		
		//closing the browser
		driver.close();
	
	}
}
