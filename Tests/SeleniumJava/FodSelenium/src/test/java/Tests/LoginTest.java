package Tests;

import java.io.FileWriter;
import java.io.IOException;
import java.util.concurrent.TimeUnit;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
//import org.openqa.selenium.firefox.FirefoxDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.testng.annotations.Test;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.AfterClass;


public class LoginTest {

        static String url;
  
        static WebDriver driver;

	@Test
	//public static void SuccessLogin(WebDriver driver, String url) 
	public static void SuccessLogin() 
        {
		try {
		driver.get(url);
		driver.findElement(By.id("id_username")).click();
		driver.findElement(By.id("id_username")).sendKeys("admin2");
		driver.findElement(By.id("id_password")).click();
		driver.findElement(By.id("id_password")).sendKeys("adminpwd1");
		driver.findElement(By.id("applybutton")).click();
		driver.findElement(By.xpath("//*[contains(text(), 'My rules')]"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
		}
	}
	@Test
	//public static void LoginWithoutLogin(WebDriver driver, String url) 
	public static void LoginWithoutLogin() 
        {
		try {
			driver.get(url);
			driver.findElement(By.id("id_username")).click();
			driver.findElement(By.id("id_username")).sendKeys("admin2");
			driver.findElement(By.id("id_password")).click();
			driver.findElement(By.id("id_password")).sendKeys("adminpwd1");
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
		}
	}
	@Test
	//public static void LoginWithoutData(WebDriver driver, String url) 
	public static void LoginWithoutData() 
        {
		try {
			driver.get(url);
			driver.findElement(By.id("id_username")).click();
			driver.findElement(By.id("id_username")).sendKeys("admin2");
			driver.findElement(By.id("id_password")).click();
			driver.findElement(By.id("id_password")).sendKeys("adminpwd1");
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
		}
	}
	@Test
	//public static void LoginWithoutPassword(WebDriver driver, String url) 
	public static void LoginWithoutPassword() 
        {
		try {
			driver.get(url);
			driver.findElement(By.id("id_username")).click();
			driver.findElement(By.id("id_username")).sendKeys("admin2");
			driver.findElement(By.id("id_password")).click();
			driver.findElement(By.id("id_password")).sendKeys("adminpwd1");
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
		}
	}
	@Test
	//public static void LoginWithWrongData(WebDriver driver, String url) 
	public static void LoginWithWrongData() 
        {
		try {
			driver.get(url);
			driver.findElement(By.id("id_username")).click();
			driver.findElement(By.id("id_username")).sendKeys("admin2");
			driver.findElement(By.id("id_password")).click();
			driver.findElement(By.id("id_password")).sendKeys("adminpwd1");
			driver.findElement(By.id("applybutton")).click();
			driver.findElement(By.xpath("//*[contains(text(), 'Please enter a correct username and password. Note that both fields are case-sensitive.')]"));
		}
		catch(Exception e) {
			try(FileWriter fileWriter = new FileWriter(".\\logs\\log.txt")) {
			    fileWriter.write(e.getMessage());
			    fileWriter.close();
			} catch (IOException ex) {
			    // Cxception handling
			}
		}
	}

        @BeforeClass
	public static void testSetUp() {
		//setting the driver executable
		System.setProperty("webdriver.chrome.driver", ".\\driver\\chromedriver.exe");
		
		// declaration and instantiation of objects/variables
    	//System.setProperty("webdriver.gecko.driver",".\\driver\\geckodriver.exe");
		//WebDriver driver = new FirefoxDriver();
		
		ChromeOptions chromeOptions = new ChromeOptions();
		//chromeOptions.addArguments("headless");
		//Initiating your chromedriver
		driver=new ChromeDriver(chromeOptions);
		
		//Applied wait time
		driver.manage().timeouts().implicitlyWait(5, TimeUnit.SECONDS);
		//maximize window
		driver.manage().window().maximize();

                url = "http://172.17.0.2:8000/altlogin";
         }
	
          public static void main(String[] args) {
    
                testSetUp();
		
		//String url = "http://172.17.0.2:8000/altlogin";
		
		//SuccessLogin(driver, url);
		SuccessLogin();
		
		//LoginWithoutLogin(driver, url);
		LoginWithoutLogin();
		
		//LoginWithoutData(driver, url);
		LoginWithoutData();
		
		//LoginWithoutPassword(driver, url);
		LoginWithoutPassword();
		
		//LoginWithWrongData(driver, url);
		LoginWithWrongData();

                testSetDown();
          }
		
        @AfterClass
        public static void testSetDown() {
		
		//closing the browser
		driver.close();
	
	}


}
